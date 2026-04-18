"""
Trakt.tv OAuth + API integration.
OAuth flow: connect → authorize → callback → store tokens → import watchlist
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings


# Trakt API base
TRAKT_API = "https://api.trakt.tv"
TRAKT_AUTH_URL = "https://api.trakt.tv/oauth/authorize"


def get_authorization_url(state: str) -> str:
    """Build the Trakt OAuth authorization URL."""
    params = {
        "response_type": "code",
        "client_id": settings.trakt_client_id,
        "redirect_uri": settings.trakt_redirect_uri,
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{TRAKT_AUTH_URL}?{query}"


async def exchange_code(code: str) -> dict[str, Any]:
    """Exchange authorization code for access/refresh tokens."""
    data = {
        "code": code,
        "client_id": settings.trakt_client_id,
        "client_secret": settings.trakt_client_secret,
        "redirect_uri": settings.trakt_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{TRAKT_API}/oauth/token", data=data)
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired access token."""
    data = {
        "refresh_token": refresh_token,
        "client_id": settings.trakt_client_id,
        "client_secret": settings.trakt_client_secret,
        "redirect_uri": settings.trakt_redirect_uri,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{TRAKT_API}/oauth/token", data=data)
        response.raise_for_status()
        return response.json()


async def get_watchlist(access_token: str) -> list[dict]:
    """Fetch user's Trakt watchlist (movies + shows)."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": settings.trakt_client_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{TRAKT_API}/users/me/watchlist",
            headers=headers,
            params={"type": "movies,shows"},
        )
        response.raise_for_status()
        return response.json()


async def get_watched_history(access_token: str) -> list[dict]:
    """Fetch user's watched history (movies + shows)."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": settings.trakt_client_id,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{TRAKT_API}/users/me/history",
            headers=headers,
            params={"type": "movies,shows"},
        )
        response.raise_for_status()
        return response.json()


def map_trakt_to_tmdb(trakt_item: dict) -> tuple[int, str] | None:
    """
    Map a Trakt watchlist item to a TMDB ID and media type.
    Returns (tmdb_id, media_type) or None if not found.
    """
    # Trakt provides tmdb_id directly in the response
    movie = trakt_item.get("movie")
    show = trakt_item.get("show")

    if movie:
        tmdb_id = movie.get("ids", {}).get("tmdb")
        if tmdb_id:
            return int(tmdb_id), "movie"

    if show:
        tmdb_id = show.get("ids", {}).get("tmdb")
        if tmdb_id:
            return int(tmdb_id), "tv"

    return None

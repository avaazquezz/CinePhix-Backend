"""
Trakt.tv integration router.

OAuth flow:
1. GET /integrations/trakt/connect → redirect to Trakt authorization
2. GET /integrations/trakt/callback → exchange code for tokens (frontend then calls /confirm)
3. POST /integrations/trakt/confirm → store tokens linked to user
4. POST /integrations/trakt/import → import watchlist + watched history
5. GET /integrations/trakt/status → check connection status
6. DELETE /integrations/trakt/disconnect → remove connection
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select

from app.config import settings
from app.dependencies import CurrentUser
from app.database import get_db
from app.models import TraktConnection, WatchlistItem
from app.services import trakt_service


router = APIRouter(prefix="/integrations/trakt", tags=["Trakt.tv"])


def _require_trakt_config():
    if not settings.trakt_client_id or not settings.trakt_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Trakt.tv integration is not configured. Set TRAKT_CLIENT_ID and TRAKT_CLIENT_SECRET.",
        )


@router.get("/connect")
async def trakt_connect(current_user: CurrentUser):
    """Start Trakt OAuth flow — returns the authorization URL for the frontend to redirect."""
    _require_trakt_config()
    state = secrets.token_urlsafe(32)
    auth_url = trakt_service.get_authorization_url(state)
    return {"authorization_url": auth_url}


@router.get("/callback")
async def trakt_callback(
    code: str = Query(..., description="Authorization code from Trakt"),
):
    """
    OAuth callback — exchanges code for tokens.
    The frontend receives these and must POST them to /confirm to link to the account.
    """
    _require_trakt_config()

    tokens = await trakt_service.exchange_code(code)
    expires_in = tokens.get("expires_in", 0)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        if expires_in else None
    )

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_at": expires_at.isoformat() if expires_at else None,
        "message": "POST these tokens to /integrations/trakt/confirm to link your account.",
    }


@router.post("/confirm")
async def trakt_confirm(
    access_token: str = Body(...),
    refresh_token: str = Body(...),
    expires_at: str | None = Body(None),
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Store Trakt tokens for the authenticated user."""
    _require_trakt_config()

    expires_dt = None
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    result = await db.execute(
        select(TraktConnection).where(TraktConnection.user_id == str(current_user.id))
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_dt
    else:
        conn = TraktConnection(
            user_id=str(current_user.id),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_dt,
        )
        db.add(conn)

    await db.commit()
    return {"ok": True, "message": "Trakt.tv connected successfully"}


@router.get("/status")
async def trakt_status(
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Check if the current user has a Trakt.tv connection."""
    result = await db.execute(
        select(TraktConnection).where(TraktConnection.user_id == str(current_user.id))
    )
    conn = result.scalar_one_or_none()

    if not conn:
        return {"connected": False, "last_sync": None}

    return {
        "connected": True,
        "last_sync": conn.last_sync.isoformat() if conn.last_sync else None,
        "expires_at": conn.expires_at.isoformat() if conn.expires_at else None,
    }


@router.post("/import")
async def trakt_import(
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Import watchlist from Trakt.tv into the user's watchlist."""
    result = await db.execute(
        select(TraktConnection).where(TraktConnection.user_id == str(current_user.id))
    )
    conn = result.scalar_one_or_none()

    if not conn:
        raise HTTPException(
            status_code=400,
            detail="Trakt.tv not connected. Call /integrations/trakt/connect first.",
        )

    # Refresh token if expired
    access_token = conn.access_token
    if conn.expires_at and conn.expires_at <= datetime.now(timezone.utc):
        tokens = await trakt_service.refresh_access_token(conn.refresh_token)
        access_token = tokens["access_token"]
        conn.access_token = access_token
        if tokens.get("refresh_token"):
            conn.refresh_token = tokens["refresh_token"]
        if tokens.get("expires_in"):
            conn.expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])

    watchlist_items = await trakt_service.get_watchlist(access_token)

    imported = 0
    for item in watchlist_items:
        mapped = trakt_service.map_trakt_to_tmdb(item)
        if not mapped:
            continue
        tmdb_id, media_type = mapped

        existing = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.tmdb_id == tmdb_id,
                WatchlistItem.media_type == media_type,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(WatchlistItem(
                user_id=current_user.id,
                tmdb_id=tmdb_id,
                media_type=media_type,
            ))
            imported += 1

    conn.last_sync = datetime.now(timezone.utc)
    await db.commit()

    return {
        "ok": True,
        "imported": imported,
        "total_watchlist_items": len(watchlist_items),
    }


@router.delete("/disconnect")
async def trakt_disconnect(
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Remove the Trakt.tv connection for the current user."""
    result = await db.execute(
        select(TraktConnection).where(TraktConnection.user_id == str(current_user.id))
    )
    conn = result.scalar_one_or_none()

    if conn:
        await db.delete(conn)
        await db.commit()

    return {"ok": True}

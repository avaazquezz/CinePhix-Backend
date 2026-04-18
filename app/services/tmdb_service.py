"""TMDB API service with Redis caching."""

import httpx

from app.config import settings
from app.utils.cache import get_cached, set_cached, TMDB_MOVIE_TTL, TMDB_TRENDING_TTL, TMDB_SEARCH_TTL
from app.schemas.media import TMDBMovieDetail, TMDBTrendingResponse, TMDBSearchResponse, TMDBGenreList, TMDBCreditsResponse


class TMDBService:
    """Service for interacting with The Movie Database API."""

    def __init__(self):
        self.api_key = settings.tmdb_api_key
        self.base_url = settings.tmdb_base_url
        self.image_base_url = settings.tmdb_image_base_url

    def _get_headers(self) -> dict[str, str]:
        """Return headers for TMDB API requests."""
        return {"Authorization": f"Bearer {self.api_key}"}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a GET request to TMDB API."""
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def get_movie(self, movie_id: int) -> TMDBMovieDetail:
        """Get movie details by ID with caching."""
        cache_key = f"tmdb:movie:{movie_id}"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBMovieDetail(**cached)

        data = await self._get(f"/movie/{movie_id}", {"api_key": self.api_key})
        await set_cached(cache_key, data, TMDB_MOVIE_TTL)
        return TMDBMovieDetail(**data)

    async def get_tv(self, tv_id: int) -> TMDBMovieDetail:
        """Get TV show details by ID with caching."""
        cache_key = f"tmdb:tv:{tv_id}"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBMovieDetail(**cached)

        data = await self._get(f"/tv/{tv_id}", {"api_key": self.api_key})
        data["media_type"] = "tv"
        await set_cached(cache_key, data, TMDB_MOVIE_TTL)
        return TMDBMovieDetail(**data)

    async def get_trending(self, media_type: str = "all", time_window: str = "day") -> TMDBTrendingResponse:
        """Get trending movies/TV with caching."""
        cache_key = f"tmdb:trending:{media_type}:{time_window}"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBTrendingResponse(**cached)

        data = await self._get(f"/trending/{media_type}/{time_window}", {"api_key": self.api_key})
        # Add media_type to each result
        for item in data.get("results", []):
            item["media_type"] = item.get("media_type", media_type if media_type != "all" else item.get("type", "movie"))
        await set_cached(cache_key, data, TMDB_TRENDING_TTL)
        return TMDBTrendingResponse(**data)

    async def search_multi(self, query: str, page: int = 1) -> TMDBSearchResponse:
        """Search movies, TV shows, and people with caching."""
        cache_key = f"tmdb:search:{query}:{page}"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBSearchResponse(**cached)

        data = await self._get("/search/multi", {"api_key": self.api_key, "query": query, "page": page})
        await set_cached(cache_key, data, TMDB_SEARCH_TTL)
        return TMDBSearchResponse(**data)

    async def get_movie_genres(self) -> list[dict]:
        """Get list of movie genres."""
        cache_key = "tmdb:genres:movies"
        cached = await get_cached(cache_key)
        if cached:
            return cached

        data = await self._get("/genre/movie/list", {"api_key": self.api_key})
        await set_cached(cache_key, data.get("genres", []), TMDB_MOVIE_TTL)
        return data.get("genres", [])

    async def get_tv_genres(self) -> list[dict]:
        """Get list of TV genres."""
        cache_key = "tmdb:genres:tv"
        cached = await get_cached(cache_key)
        if cached:
            return cached

        data = await self._get("/genre/tv/list", {"api_key": self.api_key})
        await set_cached(cache_key, data.get("genres", []), TMDB_MOVIE_TTL)
        return data.get("genres", [])

    async def get_movie_credits(self, movie_id: int) -> TMDBCreditsResponse:
        """Get movie credits (cast + crew) with caching."""
        cache_key = f"tmdb:movie:{movie_id}:credits"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBCreditsResponse(**cached)

        data = await self._get(f"/movie/{movie_id}/credits", {"api_key": self.api_key})
        await set_cached(cache_key, data, TMDB_MOVIE_TTL)
        return TMDBCreditsResponse(**data)

    async def get_tv_credits(self, tv_id: int) -> TMDBCreditsResponse:
        """Get TV show credits (cast + crew) with caching."""
        cache_key = f"tmdb:tv:{tv_id}:credits"
        cached = await get_cached(cache_key)
        if cached:
            return TMDBCreditsResponse(**cached)

        data = await self._get(f"/tv/{tv_id}/credits", {"api_key": self.api_key})
        await set_cached(cache_key, data, TMDB_MOVIE_TTL)
        return TMDBCreditsResponse(**data)

    def get_image_url(self, path: str | None, size: str = "w500") -> str | None:
        """Get full image URL from TMDB path."""
        if not path:
            return None
        return f"{self.image_base_url}/{size}{path}"
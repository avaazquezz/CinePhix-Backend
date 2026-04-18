"""TMDB proxy routes with caching."""

from fastapi import APIRouter, Query
from typing import Literal

from app.services.tmdb_service import TMDBService
from app.schemas.media import TMDBMovieDetail, TMDBTrendingResponse, TMDBSearchResponse, TMDBCreditsResponse

router = APIRouter(prefix="/tmdb", tags=["TMDB"])


@router.get("/movie/{movie_id}", response_model=TMDBMovieDetail)
async def get_movie(movie_id: int):
    """Get movie details from TMDB with caching."""
    service = TMDBService()
    return await service.get_movie(movie_id)


@router.get("/tv/{tv_id}", response_model=TMDBMovieDetail)
async def get_tv_show(tv_id: int):
    """Get TV show details from TMDB with caching."""
    service = TMDBService()
    return await service.get_tv(tv_id)


@router.get("/trending/{media_type}", response_model=TMDBTrendingResponse)
async def get_trending(
    media_type: Literal["all", "movie", "tv"],
    time_window: Literal["day", "week"] = Query(default="day"),
):
    """Get trending movies/TV from TMDB with caching."""
    service = TMDBService()
    return await service.get_trending(media_type, time_window)


@router.get("/search", response_model=TMDBSearchResponse)
async def search_multi(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    page: int = Query(default=1, ge=1, le=100),
):
    """Search movies, TV shows, and people from TMDB."""
    service = TMDBService()
    return await service.search_multi(q, page)


@router.get("/genres/movies")
async def get_movie_genres():
    """Get list of movie genres."""
    service = TMDBService()
    return {"genres": await service.get_movie_genres()}


@router.get("/genres/tv")
async def get_tv_genres():
    """Get list of TV genres."""
    service = TMDBService()
    return {"genres": await service.get_tv_genres()}


@router.get("/movie/{movie_id}/credits", response_model=TMDBCreditsResponse)
async def get_movie_credits(movie_id: int):
    """Get movie credits (cast and crew) from TMDB with caching."""
    service = TMDBService()
    return await service.get_movie_credits(movie_id)


@router.get("/tv/{tv_id}/credits", response_model=TMDBCreditsResponse)
async def get_tv_credits(tv_id: int):
    """Get TV show credits (cast and crew) from TMDB with caching."""
    service = TMDBService()
    return await service.get_tv_credits(tv_id)
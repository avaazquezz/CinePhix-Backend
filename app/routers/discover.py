"""Discovery router — advanced TMDB filtering."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser, OptionalUser
from app.services.tmdb_service import tmdb_service

router = APIRouter(prefix="/discover", tags=["Discovery"])


@router.get("/movies")
async def discover_movies(
    year: int | None = Query(None, ge=1900, le=2030, description="Filter by release year"),
    genre: str | None = Query(None, description="Genre ID from TMDB (e.g. 28 for Action)"),
    vote_min: float | None = Query(None, ge=0, le=10, description="Minimum TMDB vote average"),
    vote_max: float | None = Query(None, ge=0, le=10, description="Maximum TMDB vote average"),
    sort_by: str = Query("popularity.desc", description="Sort: popularity.desc, vote_average.desc, release_date.desc"),
    page: int = Query(1, ge=1, le=500),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Discover movies with advanced filters:
    - year: release year
    - genre: TMDB genre ID (e.g. 28=Action, 35=Comedy, 878=Sci-Fi)
    - vote_min/vote_max: TMDB vote average (0-10)
    - sort_by: popularity.desc | vote_average.desc | release_date.desc
    - page/per_page: pagination
    """
    result = await tmdb_service.discover_movies(
        year=year,
        genre=genre,
        vote_min=vote_min,
        vote_max=vote_max,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )
    return result


@router.get("/tv")
async def discover_tv(
    year: int | None = Query(None, ge=1900, le=2030, description="Filter by first air year"),
    genre: str | None = Query(None, description="Genre ID from TMDB"),
    vote_min: float | None = Query(None, ge=0, le=10),
    vote_max: float | None = Query(None, ge=0, le=10),
    sort_by: str = Query("popularity.desc", description="Sort: popularity.desc, vote_average.desc, first_air_date.desc"),
    page: int = Query(1, ge=1, le=500),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Discover TV shows with advanced filters (same params as movies).
    """
    result = await tmdb_service.discover_tv(
        year=year,
        genre=genre,
        vote_min=vote_min,
        vote_max=vote_max,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )
    return result


@router.get("/genres")
async def get_genres(
    db: AsyncSession = Depends(get_db),
):
    """Get all TMDB genres for movies and TV."""
    return await tmdb_service.get_genres()
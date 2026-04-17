"""Pydantic schemas for TMDB API responses."""

from pydantic import BaseModel
from typing import Any


class TMDBMovieDetail(BaseModel):
    """Schema for TMDB movie/TV detail response."""

    id: int
    title: str | None = None
    name: str | None = None  # For TV shows
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    release_date: str | None = None  # movies
    first_air_date: str | None = None  # TV
    media_type: str | None = None  # "movie" or "tv"
    genres: list[dict[str, Any]] = []
    runtime: int | None = None  # movies
    episode_run_time: list[int] | None = None  # TV
    status: str | None = None
    tagline: str | None = None
    imdb_id: str | None = None

    # Extra fields passthrough
    model_config = {"extra": "allow"}


class TMDBTrendingResponse(BaseModel):
    """Schema for TMDB trending response."""

    page: int
    results: list[TMDBMovieDetail]
    total_pages: int
    total_results: int


class TMDBSearchResponse(BaseModel):
    """Schema for TMDB search response."""

    page: int
    results: list[TMDBMovieDetail]
    total_pages: int
    total_results: int


class TMDBGenreList(BaseModel):
    """Schema for TMDB genre list."""

    genres: list[dict[str, Any]]


class TMDBCastMember(BaseModel):
    """Schema for a cast member in credits."""

    id: int
    name: str
    original_name: str | None = None
    character: str | None = None
    known_for_department: str | None = None
    profile_path: str | None = None
    popularity: float | None = None
    cast_id: int | None = None
    credit_id: str | None = None
    order: int | None = None


class TMDBCrewMember(BaseModel):
    """Schema for a crew member in credits."""

    id: int
    name: str
    original_name: str | None = None
    department: str | None = None
    job: str | None = None
    known_for_department: str | None = None
    profile_path: str | None = None
    popularity: float | None = None
    credit_id: str | None = None


class TMDBCreditsResponse(BaseModel):
    """Schema for TMDB credits response (cast + crew)."""

    cast: list[TMDBCastMember]
    crew: list[TMDBCrewMember]
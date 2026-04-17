"""Pydantic schemas for reviews."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MediaTypeEnum(str, Enum):
    """Media type enum."""

    MOVIE = "movie"
    TV = "tv"


class VoteTypeEnum(str, Enum):
    """Review vote type."""

    USEFUL = "useful"
    NOT_USEFUL = "not_useful"


class ReviewSortBy(str, Enum):
    """Sort options for reviews."""

    RECENT = "recent"
    TOP_RATED = "top_rated"
    MOST_USEFUL = "most_useful"


# --- Request schemas ---

class ReviewCreate(BaseModel):
    """Schema for creating a review."""

    tmdb_id: int = Field(..., description="TMDB movie or TV show ID")
    media_type: MediaTypeEnum = Field(..., description="Type: movie or tv")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    content: str = Field(..., min_length=1, max_length=5000, description="Review text")
    is_spoiler: bool = Field(default=False, description="Contains spoilers")


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    rating: int | None = Field(None, ge=1, le=5)
    content: str | None = Field(None, min_length=1, max_length=5000)
    is_spoiler: bool | None = None


class ReviewVoteCreate(BaseModel):
    """Schema for voting on a review."""

    vote_type: VoteTypeEnum


# --- Response schemas ---

class ReviewUserSummary(BaseModel):
    """Minimal user info embedded in a review."""

    id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    is_pro: bool

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    """Full review response."""

    id: UUID
    user_id: UUID
    tmdb_id: int
    media_type: MediaTypeEnum
    rating: int
    content: str
    is_spoiler: bool
    likes_count: int
    created_at: datetime
    updated_at: datetime
    user: ReviewUserSummary | None = None

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""

    items: list[ReviewResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ReviewVoteResponse(BaseModel):
    """Response after voting on a review."""

    review_id: UUID
    vote_type: VoteTypeEnum
    likes_count: int

    model_config = {"from_attributes": True}

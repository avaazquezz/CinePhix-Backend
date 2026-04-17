"""Pydantic schemas for watchlist items."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from enum import Enum


class MediaTypeEnum(str, Enum):
    """Type of media item."""

    MOVIE = "movie"
    TV = "tv"


class WatchlistItemCreate(BaseModel):
    """Schema for adding item to watchlist."""

    tmdb_id: int
    media_type: MediaTypeEnum
    notes: str | None = None


class WatchlistItemResponse(BaseModel):
    """Watchlist item response."""

    id: UUID
    tmdb_id: int
    media_type: MediaTypeEnum
    position: int
    notes: str | None
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistReorder(BaseModel):
    """Schema for reordering watchlist items."""

    position: int
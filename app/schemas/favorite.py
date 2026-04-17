"""Pydantic schemas for favorites."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from enum import Enum


class MediaTypeEnum(str, Enum):
    """Type of media item."""

    MOVIE = "movie"
    TV = "tv"


class FavoriteCreate(BaseModel):
    """Schema for marking item as favorite."""

    tmdb_id: int
    media_type: MediaTypeEnum


class FavoriteResponse(BaseModel):
    """Favorite item response."""

    id: UUID
    tmdb_id: int
    media_type: MediaTypeEnum
    added_at: datetime

    model_config = {"from_attributes": True}


class FavoriteCheck(BaseModel):
    """Response for checking if item is favorited."""

    is_favorite: bool
    favorite_id: UUID | None
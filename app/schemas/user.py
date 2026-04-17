"""Pydantic schemas for user profiles."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Public user profile response."""

    id: UUID
    email: EmailStr
    username: str
    display_name: str | None
    avatar_url: str | None
    is_pro: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = None
    username: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


class UserPreferencesResponse(BaseModel):
    """User preferences response."""

    favorite_genres: list[str] = []
    preferred_decade: str | None = None
    exclude_genres: list[str] = []
    min_rating: float | None = None
    language: str = "en"
    extra: dict = {}

    model_config = {"from_attributes": True}


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    favorite_genres: list[str] | None = None
    preferred_decade: str | None = None
    exclude_genres: list[str] | None = None
    min_rating: float | None = Field(None, ge=0, le=10)
    language: str | None = Field(None, min_length=2, max_length=10)
    extra: dict | None = None
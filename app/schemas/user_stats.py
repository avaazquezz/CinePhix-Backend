"""Pydantic schemas for user stats and follows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserStatsResponse(BaseModel):
    """User statistics response."""

    user_id: UUID
    reviews_count: int
    followers_count: int
    following_count: int
    lists_count: int
    watchlist_count: int
    favorites_count: int

    model_config = {"from_attributes": True}


class FollowResponse(BaseModel):
    """Response when following/unfollowing a user."""

    following_id: UUID
    follower_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowStatusResponse(BaseModel):
    """Check if current user follows another user."""

    is_following: bool
    followers_count: int
    following_count: int


class UserFollowSummary(BaseModel):
    """Minimal user info for follow lists."""

    id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    is_pro: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FollowersListResponse(BaseModel):
    """Paginated list of followers."""

    items: list[UserFollowSummary]
    total: int
    page: int
    per_page: int


class FollowingListResponse(BaseModel):
    """Paginated list of following."""

    items: list[UserFollowSummary]
    total: int
    page: int
    per_page: int

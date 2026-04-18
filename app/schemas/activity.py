from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    avatar: Optional[str] = None


class ActivityFeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    actor_id: UUID
    activity_type: str
    target_type: str
    target_id: int
    extra_data: dict[str, Any]
    created_at: datetime
    actor: Optional[UserBrief] = None
    user: Optional[UserBrief] = None


class PaginatedActivityResponse(BaseModel):
    items: list[ActivityFeedResponse]
    total: int
    page: int
    per_page: int
    pages: int

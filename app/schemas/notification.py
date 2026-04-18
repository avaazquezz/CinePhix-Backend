from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    type: str
    data: dict = {}


class NotificationResponse(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    read_at: Optional[datetime] = None
    created_at: datetime


class PaginatedNotificationResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    pages: int

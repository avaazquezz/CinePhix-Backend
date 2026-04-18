from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ListItemBase(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    position: Optional[int] = 0


class ListItemCreate(ListItemBase):
    pass


class ListItemResponse(ListItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_id: int
    added_at: datetime


class ListBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_public: bool = True


class ListCreate(ListBase):
    pass


class ListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    cover_image: Optional[str] = None


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    avatar: Optional[str] = None


class ListResponse(ListBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    is_featured: bool
    cover_image: Optional[str]
    items_count: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserBrief] = None
    items: Optional[list[ListItemResponse]] = None


class ListBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    is_public: bool
    is_featured: bool
    cover_image: Optional[str]
    items_count: int
    created_at: datetime
    user: Optional[UserBrief] = None

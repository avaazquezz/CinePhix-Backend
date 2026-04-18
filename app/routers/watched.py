"""User watched history and progress tracking router."""

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.watched_history import WatchedHistory

router = APIRouter(prefix="/watched", tags=["Watched"])


class WatchedCreate(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    progress_seconds: int = 0
    duration_seconds: int | None = None
    completed: bool = False


class WatchedUpdate(BaseModel):
    progress_seconds: int | None = None
    duration_seconds: int | None = None
    completed: bool | None = None


class WatchedItemResponse(BaseModel):
    id: UUID
    tmdb_id: int
    media_type: str
    watched_at: datetime
    progress_seconds: int
    duration_seconds: int | None
    completed: bool

    class Config:
        from_attributes = True


class WatchedListResponse(BaseModel):
    items: list[WatchedItemResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ProgressResponse(BaseModel):
    tmdb_id: int
    media_type: str
    progress_seconds: int
    duration_seconds: int | None
    progress_percent: float
    completed: bool


@router.post("", response_model=WatchedItemResponse, status_code=status.HTTP_201_CREATED)
async def mark_watched(
    data: Annotated[WatchedCreate, Body(...)],
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Mark a movie or TV show as watched (or update progress)."""
    result = await db.execute(
        select(WatchedHistory).where(
            and_(
                WatchedHistory.user_id == current_user.id,
                WatchedHistory.tmdb_id == data.tmdb_id,
                WatchedHistory.media_type == data.media_type,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.progress_seconds = data.progress_seconds
        if data.duration_seconds is not None:
            existing.duration_seconds = data.duration_seconds
        existing.completed = data.completed
        existing.watched_at = datetime.utcnow()
        await db.flush()
        return existing

    entry = WatchedHistory(
        user_id=current_user.id,
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        watched_at=datetime.utcnow(),
        progress_seconds=data.progress_seconds,
        duration_seconds=data.duration_seconds,
        completed=data.completed,
    )
    db.add(entry)
    await db.flush()
    return entry


@router.get("", response_model=WatchedListResponse)
async def get_watched(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    media_type: str | None = Query(None, pattern="^(movie|tv)$"),
    completed: bool | None = Query(None),
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Get current user's watched list."""
    conditions = [WatchedHistory.user_id == current_user.id]
    if media_type:
        conditions.append(WatchedHistory.media_type == media_type)
    if completed is not None:
        conditions.append(WatchedHistory.completed == completed)

    count_result = await db.execute(
        select(func.count(WatchedHistory.id)).where(*conditions)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(WatchedHistory)
        .where(*conditions)
        .order_by(desc(WatchedHistory.watched_at))
        .offset(offset)
        .limit(per_page)
    )
    items = result.scalars().all()

    pages = math.ceil(total / per_page) if per_page > 0 else 0

    return WatchedListResponse(
        items=[WatchedItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/{watched_id}", response_model=WatchedItemResponse)
async def update_progress(
    watched_id: UUID,
    data: WatchedUpdate,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Update progress for a watched entry."""
    result = await db.execute(
        select(WatchedHistory).where(
            and_(
                WatchedHistory.id == watched_id,
                WatchedHistory.user_id == current_user.id,
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Watched entry not found")

    if data.progress_seconds is not None:
        entry.progress_seconds = data.progress_seconds
    if data.duration_seconds is not None:
        entry.duration_seconds = data.duration_seconds
    if data.completed is not None:
        entry.completed = data.completed

    await db.flush()
    return entry


@router.delete("/{watched_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watched(
    watched_id: UUID,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Remove a watched entry."""
    result = await db.execute(
        select(WatchedHistory).where(
            and_(
                WatchedHistory.id == watched_id,
                WatchedHistory.user_id == current_user.id,
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Watched entry not found")

    await db.delete(entry)
    await db.flush()


@router.get("/progress/{tmdb_id}", response_model=ProgressResponse)
async def get_progress(
    tmdb_id: int,
    media_type: str = Query(..., pattern="^(movie|tv)$"),
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Get watch progress for specific media."""
    result = await db.execute(
        select(WatchedHistory).where(
            and_(
                WatchedHistory.user_id == current_user.id,
                WatchedHistory.tmdb_id == tmdb_id,
                WatchedHistory.media_type == media_type,
            )
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return ProgressResponse(
            tmdb_id=tmdb_id,
            media_type=media_type,
            progress_seconds=0,
            duration_seconds=None,
            progress_percent=0.0,
            completed=False,
        )

    percent = 0.0
    if entry.duration_seconds and entry.duration_seconds > 0:
        percent = min(100.0, (entry.progress_seconds / entry.duration_seconds) * 100)

    return ProgressResponse(
        tmdb_id=entry.tmdb_id,
        media_type=entry.media_type,
        progress_seconds=entry.progress_seconds,
        duration_seconds=entry.duration_seconds,
        progress_percent=percent,
        completed=entry.completed,
    )
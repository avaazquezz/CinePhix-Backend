"""Enhanced Activity Feed v2 router with real-time WebSocket."""

import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.activity_feed_v2 import ActivityFeedV2
from app.models.user import User
# ConnectionManager imported from notification_service

router = APIRouter(prefix="/activity", tags=["Activity"])


class ActivityEventResponse(BaseModel):
    id: UUID
    actor_id: UUID
    actor_username: str
    actor_display_name: str | None
    actor_avatar: str | None
    event_type: str
    target_type: str | None
    target_id: UUID | None
    target_title: str | None
    metadata: dict
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityFeedResponse(BaseModel):
    items: list[ActivityEventResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    pages: int


class MarkReadRequest(BaseModel):
    activity_ids: list[UUID] | None = None
    mark_all: bool = False


async def _build_event_response(event: ActivityFeedV2, user: User) -> ActivityEventResponse:
    actor = event.actor
    target_title = None
    if event.event_metadata:
        target_title = event.event_metadata.get("title") or event.event_metadata.get("list_name")

    return ActivityEventResponse(
        id=event.id,
        actor_id=event.actor_id,
        actor_username=actor.username if actor else "unknown",
        actor_display_name=getattr(actor, 'display_name', None) if actor else None,
        actor_avatar=getattr(actor, 'avatar_url', None) if actor else None,
        event_type=event.event_type,
        target_type=event.target_type,
        target_id=event.target_id,
        target_title=target_title,
        metadata=event.event_metadata or {},
        is_read=event.is_read,
        created_at=event.created_at,
    )


async def _emit_activity(user_id: UUID, db, event: ActivityFeedV2 = None):
    """Send a notification WebSocket ping to the user."""
    if not manager:
        return
    try:
        from app.services.notification_service import manager as nm
        # Reload to get current manager state
        from app.database import AsyncSession
        async with db.begin():
            if event:
                resp = await _build_event_response(event, None)
                await nm.send_to_user(str(user_id), {
                    "type": "activity",
                    "event": resp.model_dump(mode="json"),
                })
    except Exception:
        pass


@router.get("/feed/v2", response_model=ActivityFeedResponse)
async def get_activity_feed_v2(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    event_type: str | None = Query(None, description="Filter: follow | like | comment | review | list | watch"),
    unread_only: bool = Query(False),
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Get enhanced activity feed v2 for the current user."""
    filters = [ActivityFeedV2.user_id == current_user.id]

    if event_type:
        filters.append(ActivityFeedV2.event_type == event_type)

    if unread_only:
        filters.append(ActivityFeedV2.is_read == False)

    # Count total + unread
    count_query = select(func.count(ActivityFeedV2.id)).where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    unread_query = select(func.count(ActivityFeedV2.id)).where(
        and_(ActivityFeedV2.user_id == current_user.id, ActivityFeedV2.is_read == False)
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar_one()

    offset = (page - 1) * per_page
    query = (
        select(ActivityFeedV2)
        .options(selectinload(ActivityFeedV2.actor))
        .where(and_(*filters))
        .order_by(desc(ActivityFeedV2.created_at))
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    events = result.scalars().all()

    items = [await _build_event_response(e, current_user) for e in events]

    return ActivityFeedResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.post("/feed/v2/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_activity_read(
    data: MarkReadRequest,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Mark activity items as read."""
    if data.mark_all:
        await db.execute(
            select(ActivityFeedV2)
            .where(and_(
                ActivityFeedV2.user_id == current_user.id,
                ActivityFeedV2.is_read == False
            ))
        )
        await db.execute(
            select(ActivityFeedV2)
            .where(and_(
                ActivityFeedV2.user_id == current_user.id,
                ActivityFeedV2.is_read == False
            ))
            .update({ActivityFeedV2.is_read: True})
        )
    elif data.activity_ids:
        await db.execute(
            select(ActivityFeedV2)
            .where(and_(
                ActivityFeedV2.id.in_(data.activity_ids),
                ActivityFeedV2.user_id == current_user.id
            ))
            .update({ActivityFeedV2.is_read: True})
        )
    await db.flush()


@router.delete("/feed/v2", status_code=status.HTTP_204_NO_CONTENT)
async def clear_activity_feed(
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Clear all activity for the current user."""
    from sqlalchemy import delete
    await db.execute(
        delete(ActivityFeedV2).where(ActivityFeedV2.user_id == current_user.id)
    )
    await db.flush()


async def record_activity(
    db,
    user_id: UUID,
    actor_id: UUID,
    event_type: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    metadata: dict | None = None,
):
    """Record an activity event in the feed."""
    event = ActivityFeedV2(
        user_id=user_id,
        actor_id=actor_id,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )
    db.add(event)
    await db.flush()

    # Send real-time notification via WebSocket
    try:
        from app.main import notification_manager
        resp = await _build_event_response(event, None)
        await notification_manager.send_to_user(str(user_id), {
            "type": "activity",
            "event": resp.model_dump(mode="json"),
        })
    except Exception:
        pass

    return event

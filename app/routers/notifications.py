"""
Notification router — inbox + read state management.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update, func as sql_func, update
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DBSession
from app.models import Notification
from app.schemas.notification import NotificationResponse, PaginatedNotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedNotificationResponse)
async def list_notifications(
    current_user: CurrentUser,
    *,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    unread_only: bool = Query(False),
    db: DBSession,
):
    """Get paginated notifications for the current user."""
    offset = (page - 1) * per_page

    # Base query — only for this user
    base_query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        base_query = base_query.where(Notification.read_at.is_(None))

    # Total count
    total_query = select(sql_func.count()).select_from(base_query.subquery())
    total = (await db.execute(total_query)).scalar()

    # Unread count
    unread_query = select(sql_func.count()).where(
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None),
    )
    unread_count = (await db.execute(unread_query)).scalar()

    # Paginated results
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedNotificationResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read_at = sql_func.now()
    await db.commit()
    return {"ok": True}


@router.put("/read-all")
async def mark_all_read(
    current_user: CurrentUser,
    db: DBSession,
):
    """Mark all unread notifications as read."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=sql_func.now())
    )
    await db.commit()
    return {"ok": True}


@router.get("/unread-count")
async def unread_count(
    current_user: CurrentUser,
    db: DBSession,
):
    """Get unread notification count."""
    result = await db.execute(
        select(sql_func.count()).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    count = result.scalar()
    return {"unread_count": count}

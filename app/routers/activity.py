"""
Activity Feed router — timeline of followed users' activity.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser, OptionalUser, DBSession
from app.models import User, ActivityFeed, UserFollow
from app.schemas.activity import ActivityFeedResponse, PaginatedActivityResponse

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/me", response_model=PaginatedActivityResponse)
async def get_my_activity_feed(
    current_user: CurrentUser,
    *,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: DBSession,
):
    """
    Get activity feed for the current user — shows activity
    from followed users and the user's own activity.
    """
    offset = (page - 1) * per_page

    # Get list of user IDs the current user follows
    following_result = await db.execute(
        select(UserFollow.following_id).where(
            UserFollow.follower_id == current_user.id
        )
    )
    following_ids = [str(r[0]) for r in following_result.fetchall()]
    
    # Include own user ID too
    user_ids = following_ids + [str(current_user.id)]

    # Query activity
    count_result = await db.execute(
        select(ActivityFeed)
        .where(
            ActivityFeed.user_id.in_([uid for uid in user_ids])
        )
    )
    total = len(count_result.scalars().all())

    result = await db.execute(
        select(ActivityFeed)
        .where(ActivityFeed.user_id.in_([uid for uid in user_ids]))
        .order_by(ActivityFeed.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    activities = result.scalars().all()

    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedActivityResponse(
        items=activities,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/user/{user_id}", response_model=PaginatedActivityResponse)
async def get_user_activity(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get public activity for a specific user."""
    offset = (page - 1) * per_page

    # Count total
    count_result = await db.execute(
        select(ActivityFeed).where(
            ActivityFeed.user_id == user_id
        )
    )
    total = len(count_result.scalars().all())

    result = await db.execute(
        select(ActivityFeed)
        .where(ActivityFeed.user_id == user_id)
        .order_by(ActivityFeed.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    activities = result.scalars().all()

    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedActivityResponse(
        items=activities,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/public", response_model=PaginatedActivityResponse)
async def get_public_activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    activity_type: Optional[str] = Query(None, description="Filter by type: review, follow, list, watchlist"),
    db: AsyncSession = Depends(get_db),
):
    """Get public activity feed (global timeline)."""
    offset = (page - 1) * per_page

    query = select(ActivityFeed).order_by(ActivityFeed.created_at.desc())
    count_query = select(ActivityFeed)

    if activity_type:
        query = query.where(ActivityFeed.activity_type == activity_type)
        count_query = count_query.where(ActivityFeed.activity_type == activity_type)

    # Count
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    result = await db.execute(
        query.offset(offset).limit(per_page)
    )
    activities = result.scalars().all()

    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedActivityResponse(
        items=activities,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )

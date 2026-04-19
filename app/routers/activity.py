"""
Activity Feed router — timeline of followed users' activity.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser, DBSession
from app.models import User, ActivityFeed, UserFollow
from app.schemas.activity import ActivityFeedResponse, PaginatedActivityResponse

router = APIRouter(prefix="/activity", tags=["activity"])


def _activity_query_with_relations():
    """Base query with eager loading of actor and user relations."""
    return select(ActivityFeed).options(
        selectinload(ActivityFeed.actor),
        selectinload(ActivityFeed.user),
    )


@router.get("/me", response_model=PaginatedActivityResponse)
async def get_my_activity_feed(
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
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

    # Count total
    count_result = await db.execute(
        select(func.count(ActivityFeed.id)).where(
            ActivityFeed.user_id.in_(user_ids)
        )
    )
    total = count_result.scalar() or 0

    # Query with eager-loaded relations
    result = await db.execute(
        _activity_query_with_relations()
        .where(ActivityFeed.user_id.in_(user_ids))
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
    db=Depends(get_db),
):
    """Get public activity for a specific user."""
    offset = (page - 1) * per_page

    # Count total
    count_result = await db.execute(
        select(func.count(ActivityFeed.id)).where(
            ActivityFeed.user_id == user_id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        _activity_query_with_relations()
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
    activity_type: Optional[str] = Query(
        None, description="Filter by type: review, follow, list, watchlist"
    ),
    db=Depends(get_db),
):
    """Get public activity feed (global timeline)."""
    offset = (page - 1) * per_page

    base_filter = []
    if activity_type:
        base_filter.append(ActivityFeed.activity_type == activity_type)

    # Count total
    count_query = select(func.count(ActivityFeed.id))
    if base_filter:
        count_query = count_query.where(*base_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Query with eager-loaded relations
    query = _activity_query_with_relations()
    if base_filter:
        query = query.where(*base_filter)
    result = await db.execute(
        query.order_by(ActivityFeed.created_at.desc())
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

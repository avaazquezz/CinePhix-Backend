"""User follows router for follow/unfollow functionality."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser, OptionalUser
from app.models import User, UserFollow, UserStats
from app.schemas.user_stats import (
    FollowersListResponse,
    FollowStatusResponse,
    FollowingListResponse,
    FollowResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/{user_id}/follow", response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Follow another user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself",
        )

    # Check target user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if already following
    existing = await db.execute(
        select(UserFollow).where(
            and_(
                UserFollow.follower_id == current_user.id,
                UserFollow.following_id == user_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already following this user",
        )

    follow = UserFollow(follower_id=current_user.id, following_id=user_id)
    db.add(follow)
    await db.flush()

    # Update stats for both users
    await _increment_followers_count(db, user_id, +1)
    await _increment_following_count(db, current_user.id, +1)

    return follow


@router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    user_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Unfollow a user."""
    result = await db.execute(
        select(UserFollow).where(
            and_(
                UserFollow.follower_id == current_user.id,
                UserFollow.following_id == user_id,
            )
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not following this user",
        )

    await db.delete(follow)
    await db.flush()

    # Update stats
    await _increment_followers_count(db, user_id, -1)
    await _increment_following_count(db, current_user.id, -1)


@router.get("/{user_id}/followers", response_model=FollowersListResponse)
async def get_followers(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get a user's followers."""
    # Count total
    count_result = await db.execute(
        select(func.count(UserFollow.id)).where(UserFollow.following_id == user_id)
    )
    total = count_result.scalar_one()

    # Get followers with user info
    offset = (page - 1) * per_page
    result = await db.execute(
        select(UserFollow)
        .options(selectinload(UserFollow.follower))
        .where(UserFollow.following_id == user_id)
        .order_by(UserFollow.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    follows = result.scalars().all()

    items = [f.follower for f in follows if f.follower is not None]

    return FollowersListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}/following", response_model=FollowingListResponse)
async def get_following(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get users a user is following."""
    # Count total
    count_result = await db.execute(
        select(func.count(UserFollow.id)).where(UserFollow.follower_id == user_id)
    )
    total = count_result.scalar_one()

    # Get following with user info
    offset = (page - 1) * per_page
    result = await db.execute(
        select(UserFollow)
        .options(selectinload(UserFollow.following))
        .where(UserFollow.follower_id == user_id)
        .order_by(UserFollow.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    follows = result.scalars().all()

    items = [f.following for f in follows if f.following is not None]

    return FollowingListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}/follow-status", response_model=FollowStatusResponse)
async def get_follow_status(
    user_id: UUID,
    current_user: OptionalUser,
    db: AsyncSession = Depends(get_db),
):
    """Check if current user follows another user and get counts."""
    is_following = False

    if current_user:
        result = await db.execute(
            select(UserFollow).where(
                and_(
                    UserFollow.follower_id == current_user.id,
                    UserFollow.following_id == user_id,
                )
            )
        )
        is_following = result.scalar_one_or_none() is not None

    # Get follower/following counts
    followers_count = await db.execute(
        select(func.count(UserFollow.id)).where(UserFollow.following_id == user_id)
    )
    following_count = await db.execute(
        select(func.count(UserFollow.id)).where(UserFollow.follower_id == user_id)
    )

    return FollowStatusResponse(
        is_following=is_following,
        followers_count=followers_count.scalar_one(),
        following_count=following_count.scalar_one(),
    )


# --- Helper functions ---

async def _increment_followers_count(db: AsyncSession, user_id: UUID, delta: int):
    """Update followers_count for a user."""
    result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    stats.followers_count = max(0, (stats.followers_count or 0) + delta)
    await db.flush()


async def _increment_following_count(db: AsyncSession, user_id: UUID, delta: int):
    """Update following_count for a user."""
    result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    stats.following_count = max(0, (stats.following_count or 0) + delta)
    await db.flush()

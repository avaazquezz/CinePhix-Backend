"""User stats router for public statistics."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import OptionalUser
from app.models import User, UserStats
from app.schemas.user_stats import UserStatsResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get public stats for a user.
    Accepts both user UUID and username as user_id.
    """
    # Try to resolve user_id: first as UUID, then as username
    target_uuid = None

    # Try parsing as UUID
    try:
        target_uuid = UUID(user_id)
    except ValueError:
        # Not a UUID — try username lookup
        result = await db.execute(select(User).where(User.username == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        target_uuid = user.id

    result = await db.execute(select(UserStats).where(UserStats.user_id == target_uuid))
    stats = result.scalar_one_or_none()

    if not stats:
        # Return zeros if no stats record yet
        return UserStatsResponse(
            user_id=target_uuid,
            reviews_count=0,
            followers_count=0,
            following_count=0,
            lists_count=0,
            watchlist_count=0,
            favorites_count=0,
        )

    return stats

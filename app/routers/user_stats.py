"""User stats router for public statistics."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import OptionalUser
from app.models import User, UserStats
from app.schemas.user_stats import UserStatsResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get public stats for a user."""
    result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        # Return zeros if no stats record yet
        return UserStatsResponse(
            user_id=user_id,
            reviews_count=0,
            followers_count=0,
            following_count=0,
            lists_count=0,
            watchlist_count=0,
            favorites_count=0,
        )

    return stats

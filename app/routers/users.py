"""User profile routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.review import ReviewResponse, ReviewListResponse
from app.schemas.list import ListResponse
from app.dependencies import CurrentUser
from app.models.user import User, UserPreferences
from app.models import UserStats, Review, List as UserList

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    """Get current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return current_user

    # Check username uniqueness if updating
    if "username" in update_data:
        result = await db.execute(
            select(User).where(User.username == update_data["username"], User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    for key, value in update_data.items():
        setattr(current_user, key, value)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's preferences."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Return default preferences
        return UserPreferencesResponse()

    return preferences


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    data: UserPreferencesUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update current user's preferences."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create preferences
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        await db.flush()

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(preferences, key, value)

    await db.flush()
    return preferences


@router.get("/{username}", response_model=UserResponse)
async def get_public_user_profile(username: str, db: AsyncSession = Depends(get_db)):
    """Get public profile of any user by username."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Fetch user stats
    stats_result = await db.execute(select(UserStats).where(UserStats.user_id == user.id))
    stats = stats_result.scalar_one_or_none()

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        is_pro=user.is_pro,
        created_at=user.created_at,
        reviews_count=stats.reviews_count if stats else 0,
        followers_count=stats.followers_count if stats else 0,
        following_count=stats.following_count if stats else 0,
    )

@router.get("/{username}/reviews", response_model=ReviewListResponse)
async def get_public_user_reviews(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public reviews by username."""


    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reviews_result = await db.execute(
        select(Review)
        .where(Review.user_id == user.id)
        .order_by(Review.created_at.desc())
    )
    reviews = reviews_result.scalars().all()

    return ReviewListResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=len(reviews),
        page=1,
        per_page=20,
        pages=1,
    )


@router.get("/{username}/lists")
async def get_public_user_lists(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public lists by username."""


    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    lists_result = await db.execute(
        select(UserList)
        .where(UserList.user_id == user.id, UserList.is_public == True)  # noqa: E712
        .order_by(UserList.created_at.desc())
    )
    lists = lists_result.scalars().all()

    return {
        "lists": [ListResponse.model_validate(l) for l in lists],
        "total": len(lists),
    }

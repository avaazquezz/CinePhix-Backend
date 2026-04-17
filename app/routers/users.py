"""User profile routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, UserPreferencesResponse, UserPreferencesUpdate
from app.dependencies import CurrentUser
from app.models.user import User, UserPreferences

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

    return user
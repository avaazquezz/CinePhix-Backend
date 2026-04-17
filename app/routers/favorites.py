"""Favorites routes for managing user's favorite movies/TV shows."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.favorite import FavoriteCreate, FavoriteResponse, FavoriteCheck
from app.dependencies import CurrentUser
from app.models.favorite import Favorite

router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.get("", response_model=list[FavoriteResponse])
async def get_favorites(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Get current user's favorite items."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.added_at.desc())
    )
    items = result.scalars().all()
    return items


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    data: FavoriteCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Mark an item as favorite."""
    # Check if already favorited
    existing = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.tmdb_id == data.tmdb_id,
                Favorite.media_type == data.media_type.value,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item already in favorites")

    favorite = Favorite(
        user_id=current_user.id,
        tmdb_id=data.tmdb_id,
        media_type=data.media_type.value,
    )
    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)
    return favorite


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    favorite_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from favorites."""
    result = await db.execute(
        select(Favorite).where(
            and_(Favorite.id == favorite_id, Favorite.user_id == current_user.id)
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")

    await db.delete(favorite)
    await db.flush()


@router.get("/check/{tmdb_id}", response_model=FavoriteCheck)
async def check_is_favorite(
    tmdb_id: int,
    media_type: str = "movie",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a specific item is in user's favorites."""
    result = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.tmdb_id == tmdb_id,
                Favorite.media_type == media_type,
            )
        )
    )
    favorite = result.scalar_one_or_none()

    return FavoriteCheck(is_favorite=favorite is not None, favorite_id=favorite.id if favorite else None)


from app.dependencies import get_current_user
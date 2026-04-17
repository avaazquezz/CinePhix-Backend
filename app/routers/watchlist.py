"""Watchlist routes for managing user's watchlist."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistReorder
from app.dependencies import CurrentUser
from app.models.watchlist import WatchlistItem
from app.models.user import User

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Get current user's watchlist sorted by position."""
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.position)
    )
    items = result.scalars().all()
    return items


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: WatchlistItemCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Add an item to the user's watchlist."""
    # Check if already exists
    existing = await db.execute(
        select(WatchlistItem).where(
            and_(
                WatchlistItem.user_id == current_user.id,
                WatchlistItem.tmdb_id == data.tmdb_id,
                WatchlistItem.media_type == data.media_type.value,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item already in watchlist")

    # Get max position
    max_pos_result = await db.execute(
        select(WatchlistItem.position)
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(WatchlistItem.position.desc())
        .limit(1)
    )
    max_pos = max_pos_result.scalar_one_or_none() or 0

    item = WatchlistItem(
        user_id=current_user.id,
        tmdb_id=data.tmdb_id,
        media_type=data.media_type.value,
        position=max_pos + 1,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    item_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove an item from the user's watchlist."""
    result = await db.execute(
        select(WatchlistItem).where(
            and_(WatchlistItem.id == item_id, WatchlistItem.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in watchlist")

    await db.delete(item)
    await db.flush()


@router.patch("/{item_id}", response_model=WatchlistItemResponse)
async def reorder_watchlist_item(
    item_id: UUID,
    data: WatchlistReorder,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Reorder a watchlist item (change its position)."""
    result = await db.execute(
        select(WatchlistItem).where(
            and_(WatchlistItem.id == item_id, WatchlistItem.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in watchlist")

    item.position = data.position
    await db.flush()
    await db.refresh(item)
    return item
"""
Lists router — CRUD for public lists and list items.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser, OptionalUser, DBSession
from app.models import User, List as ListModel, ListItem, ActivityFeed
from app.schemas.list import (
    ListCreate,
    ListUpdate,
    ListResponse,
    ListBriefResponse,
    ListItemCreate,
    ListItemResponse,
)

router = APIRouter(prefix="/lists", tags=["lists"])


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "is_pro": user.is_pro,
    }


async def _create_activity(
    db: AsyncSession,
    user_id: str,
    actor_id: str,
    activity_type: str,
    target_type: str,
    target_id: int,
    metadata: dict = None,
) -> None:
    """Helper to create an activity feed entry."""
    activity = ActivityFeed(
        user_id=user_id,
        actor_id=actor_id,
        activity_type=activity_type,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )
    db.add(activity)


# ─── LISTS CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=ListResponse)
async def create_list(
    data: ListCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Create a new list."""
    # Check if user already has a list with this name
    existing = await db.execute(
        select(ListModel).where(
            ListModel.user_id == current_user.id,
            ListModel.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="List with this name already exists")

    new_list = ListModel(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(new_list)
    await db.flush()

    # Create activity
    await _create_activity(
        db,
        user_id=str(current_user.id),
        actor_id=str(current_user.id),
        activity_type="created_list",
        target_type="list",
        target_id=new_list.id,
        metadata={"list_name": data.name},
    )

    await db.commit()
    await db.refresh(new_list)
    new_list.user = current_user
    return new_list


@router.get("", response_model=list[ListBriefResponse])
async def get_my_lists(
    current_user: CurrentUser,
    db: DBSession,
):
    """Get all lists belonging to the current user."""
    result = await db.execute(
        select(ListModel)
        .where(ListModel.user_id == current_user.id)
        .options(selectinload(ListModel.user))
        .order_by(ListModel.created_at.desc())
    )
    lists = result.scalars().all()
    return lists


@router.get("/public", response_model=list[ListBriefResponse])
async def get_public_lists(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get all public lists, optionally featured first."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ListModel)
        .where(ListModel.is_public == True)
        .options(selectinload(ListModel.user))
        .order_by(ListModel.is_featured.desc(), ListModel.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.get("/featured", response_model=list[ListBriefResponse])
async def get_featured_lists(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get featured public lists."""
    result = await db.execute(
        select(ListModel)
        .where(ListModel.is_public == True, ListModel.is_featured == True)
        .options(selectinload(ListModel.user))
        .order_by(ListModel.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{list_id}", response_model=ListResponse)
async def get_list(
    list_id: int,
    current_user: OptionalUser,
    db: DBSession,
):
    """Get a list by ID. Returns 404 if private and not owner."""
    result = await db.execute(
        select(ListModel)
        .options(selectinload(ListModel.user), selectinload(ListModel.items))
        .where(ListModel.id == list_id)
    )
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if not lst.is_public and (not current_user or str(current_user.id) != str(lst.user_id)):
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.put("/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: int,
    data: ListUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update a list (owner only)."""
    result = await db.execute(
        select(ListModel)
        .options(selectinload(ListModel.user), selectinload(ListModel.items))
        .where(ListModel.id == list_id)
    )
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if str(lst.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your list")

    if data.name is not None:
        lst.name = data.name
    if data.description is not None:
        lst.description = data.description
    if data.is_public is not None:
        lst.is_public = data.is_public
    if data.cover_image is not None:
        lst.cover_image = data.cover_image

    await db.commit()
    await db.refresh(lst)
    return lst


@router.delete("/{list_id}")
async def delete_list(
    list_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """Delete a list (owner only)."""
    result = await db.execute(
        select(ListModel).where(ListModel.id == list_id)
    )
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if str(lst.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your list")

    await db.execute(delete(ListModel).where(ListModel.id == list_id))
    await db.commit()
    return {"ok": True}


# ─── LIST ITEMS ───────────────────────────────────────────────────────────────

@router.post("/{list_id}/items", response_model=ListItemResponse)
async def add_item_to_list(
    list_id: int,
    data: ListItemCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Add an item to a list (owner only)."""
    result = await db.execute(
        select(ListModel).where(ListModel.id == list_id)
    )
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if str(lst.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your list")

    # Check if item already in list
    existing = await db.execute(
        select(ListItem).where(
            ListItem.list_id == list_id,
            ListItem.tmdb_id == data.tmdb_id,
            ListItem.media_type == data.media_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Item already in list")

    # Get current max position
    max_pos = await db.execute(
        select(func.max(ListItem.position)).where(ListItem.list_id == list_id)
    )
    max_position = max_pos.scalar() or 0

    item = ListItem(
        list_id=list_id,
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        position=data.position if data.position is not None else max_position + 1,
    )
    db.add(item)
    lst.items_count += 1

    # Activity
    await _create_activity(
        db,
        user_id=str(current_user.id),
        actor_id=str(current_user.id),
        activity_type="added_to_list",
        target_type=data.media_type,
        target_id=data.tmdb_id,
        metadata={"list_id": list_id, "list_name": lst.name},
    )

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{list_id}/items/{tmdb_id}/{media_type}")
async def remove_item_from_list(
    list_id: int,
    tmdb_id: int,
    media_type: str,
    current_user: CurrentUser,
    db: DBSession,
):
    """Remove an item from a list (owner only)."""
    result = await db.execute(
        select(ListModel).where(ListModel.id == list_id)
    )
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    if str(lst.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your list")

    result = await db.execute(
        delete(ListItem).where(
            ListItem.list_id == list_id,
            ListItem.tmdb_id == tmdb_id,
            ListItem.media_type == media_type,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Item not in list")

    lst.items_count = max(0, lst.items_count - 1)
    await db.commit()
    return {"ok": True}


@router.get("/{list_id}/items", response_model=list[ListItemResponse])
async def get_list_items(
    list_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all items in a list."""
    result = await db.execute(
        select(ListItem)
        .where(ListItem.list_id == list_id)
        .order_by(ListItem.position)
    )
    return result.scalars().all()

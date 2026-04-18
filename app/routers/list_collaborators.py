"""List collaborators router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.list import List
from app.models.list_item import ListItem
from sqlalchemy import select, and_, or_

router = APIRouter(prefix="/lists", tags=["Lists"])


class CollaboratorResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None


class CollaboratorListResponse(BaseModel):
    collaborators: list[CollaboratorResponse]


async def _get_list_or_404(db, list_id: int, current_user: CurrentUser) -> List:
    result = await db.execute(select(List).where(List.id == list_id))
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    # Only owner or collaborators can manage
    if lst.user_id != current_user.id:
        # Check if current_user is in collaborators JSON
        collaborators = lst.collaborators or []
        if str(current_user.id) not in collaborators:
            raise HTTPException(status_code=403, detail="Not authorized")
    return lst


@router.get("/{list_id}/collaborators", response_model=CollaboratorListResponse)
async def get_collaborators(
    list_id: int,
    db=Depends(get_db),
):
    """Get list of collaborators for a list."""
    from app.models import User

    result = await db.execute(select(List).where(List.id == list_id))
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    collaborators = lst.collaborators or []
    if not collaborators:
        return CollaboratorListResponse(collaborators=[])

    # Fetch user details for each collaborator
    items = []
    for cid in collaborators:
        user_result = await db.execute(select(User).where(User.id == UUID(cid)))
        user = user_result.scalar_one_or_none()
        if user:
            items.append(CollaboratorResponse(
                user_id=user.id,
                username=user.username,
                display_name=getattr(user, 'display_name', None),
                avatar_url=getattr(user, 'avatar_url', None),
            ))

    return CollaboratorListResponse(collaborators=items)


@router.post("/{list_id}/collaborators", response_model=CollaboratorListResponse, status_code=status.HTTP_201_CREATED)
async def add_collaborator(
    list_id: int,
    username: str = Query(..., description="Username to add as collaborator"),
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Add a collaborator to a list (owner only)."""
    from app.models import User

    # Get list
    result = await db.execute(select(List).where(List.id == list_id))
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    # Only owner can add collaborators
    if lst.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can add collaborators")

    # Find user by username
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == lst.user_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as collaborator")

    # Add to collaborators
    collaborators = lst.collaborators or []
    if str(user.id) not in collaborators:
        collaborators.append(str(user.id))
        lst.collaborators = collaborators
        await db.flush()

    # Return updated list
    return await get_collaborators(list_id, db)


@router.delete("/{list_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_collaborator(
    list_id: int,
    user_id: int,
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Remove a collaborator from a list (owner only)."""
    result = await db.execute(select(List).where(List.id == list_id))
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    if lst.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can remove collaborators")

    collaborators = lst.collaborators or []
    uid_str = str(user_id)
    if uid_str in collaborators:
        collaborators.remove(uid_str)
        lst.collaborators = collaborators
        await db.flush()
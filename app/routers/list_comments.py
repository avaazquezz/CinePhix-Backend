"""List comments router."""

import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.list_comment import ListComment
from app.models.list import List

router = APIRouter(prefix="/lists", tags=["Lists"])


class CommentCreate(BaseModel):
    content: str = Query(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    id: UUID
    list_id: int
    user_id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    per_page: int
    pages: int


async def _get_list_or_404(db, list_id: int) -> List:
    result = await db.execute(select(List).where(List.id == list_id))
    lst = result.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.get("/{list_id}/comments", response_model=CommentListResponse)
async def get_comments(
    list_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """Get comments for a list."""
    await _get_list_or_404(db, list_id)

    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    count_result = await db.execute(
        select(func.count(ListComment.id)).where(ListComment.list_id == list_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(ListComment)
        .options(selectinload(ListComment.user))
        .where(ListComment.list_id == list_id)
        .order_by(ListComment.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    comments = result.scalars().all()

    items = []
    for c in comments:
        user = c.user
        items.append(CommentResponse(
            id=c.id,
            list_id=c.list_id,
            user_id=c.user_id,
            username=user.username if user else "unknown",
            display_name=getattr(user, 'display_name', None),
            avatar_url=getattr(user, 'avatar_url', None),
            content=c.content,
            created_at=c.created_at,
        ))

    return CommentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.post("/{list_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    list_id: int,
    data: CommentCreate,
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Add a comment to a list."""
    lst = await _get_list_or_404(db, list_id)

    comment = ListComment(
        list_id=list_id,
        user_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    user = comment.user

    return CommentResponse(
        id=comment.id,
        list_id=comment.list_id,
        user_id=comment.user_id,
        username=current_user.username,
        display_name=getattr(user, 'display_name', None) if user else None,
        avatar_url=getattr(user, 'avatar_url', None) if user else None,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Delete a comment (owner only)."""
    from sqlalchemy import select

    result = await db.execute(
        select(ListComment).where(ListComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your comment")

    await db.delete(comment)
    await db.flush()
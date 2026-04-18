"""Review comments router."""

import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.review import Review
from app.models.review_comment import ReviewComment

router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ReviewCommentCreate(BaseModel):
    content: str = Query(..., min_length=1, max_length=1000)


class ReviewCommentResponse(BaseModel):
    id: UUID
    review_id: UUID
    user_id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCommentListResponse(BaseModel):
    items: list[ReviewCommentResponse]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/{review_id}/comments", response_model=ReviewCommentListResponse)
async def get_review_comments(
    review_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """Get comments on a review."""
    # Check review exists
    result = await db.execute(select(Review).where(Review.id == review_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Review not found")

    count_result = await db.execute(
        select(func.count(ReviewComment.id)).where(ReviewComment.review_id == review_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(ReviewComment)
        .options(selectinload(ReviewComment.user))
        .where(ReviewComment.review_id == review_id)
        .order_by(ReviewComment.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    comments = result.scalars().all()

    items = []
    for c in comments:
        user = c.user
        items.append(ReviewCommentResponse(
            id=c.id,
            review_id=c.review_id,
            user_id=c.user_id,
            username=user.username if user else "unknown",
            display_name=getattr(user, 'display_name', None),
            avatar_url=getattr(user, 'avatar_url', None),
            content=c.content,
            created_at=c.created_at,
        ))

    return ReviewCommentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.post("/{review_id}/comments", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_review_comment(
    review_id: UUID,
    data: ReviewCommentCreate,
    *,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Add a comment to a review."""
    # Check review exists
    result = await db.execute(select(Review).where(Review.id == review_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Review not found")

    comment = ReviewComment(
        review_id=review_id,
        user_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)

    user = comment.user

    return ReviewCommentResponse(
        id=comment.id,
        review_id=comment.review_id,
        user_id=comment.user_id,
        username=current_user.username,
        display_name=getattr(user, 'display_name', None) if user else None,
        avatar_url=getattr(user, 'avatar_url', None) if user else None,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_comment(
    comment_id: UUID,
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Delete a comment (owner only)."""
    result = await db.execute(
        select(ReviewComment).where(ReviewComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your comment")

    await db.delete(comment)
    await db.flush()

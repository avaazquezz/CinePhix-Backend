"""Follow System v2 — follow requests, pending requests, accept/reject."""

import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.follow_request import FollowRequest
from app.models.follow import UserFollow as Follow
from app.models.user import User
from app.routers.activity_v2 import record_activity

router = APIRouter(prefix="/users", tags=["Users"])


class FollowRequestResponse(BaseModel):
    id: UUID
    from_user_id: UUID
    from_username: str
    from_display_name: str | None
    from_avatar: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class FollowRequestListResponse(BaseModel):
    items: list[FollowRequestResponse]
    total: int


class FollowUserResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    is_following: bool
    is_pending: bool
    created_at: datetime | None

    class Config:
        from_attributes = True


class FollowListResponse(BaseModel):
    items: list[FollowUserResponse]
    total: int
    page: int
    per_page: int
    pages: int


async def _get_user_or_404(db, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


async def _get_follow_status_for_user(db, target_user_id: UUID, current_user: CurrentUser) -> dict:
    """Check if current_user follows target_user_id."""
    result = await db.execute(
        select(Follow).where(and_(
            Follow.follower_id == current_user.id,
            Follow.following_id == target_user_id
        ))
    )
    follow = result.scalar_one_or_none()

    pending = False
    if not follow:
        # Check for pending request
        req_result = await db.execute(
            select(FollowRequest).where(and_(
                FollowRequest.from_user_id == current_user.id,
                FollowRequest.to_user_id == target_user_id,
                FollowRequest.status == "pending"
            ))
        )
        req = req_result.scalar_one_or_none()
        pending = req is not None

    return {"is_following": follow is not None, "is_pending": pending}


async def _parse_user_id(user_id_str: str, current_user: CurrentUser) -> UUID:
    """Parse user_id string, treating 'me' as current user's ID."""
    if user_id_str == "me":
        return current_user.id
    return UUID(user_id_str)


# ─── Follow Requests ────────────────────────────────────────────────────────

@router.post("/{user_id}/follow-request", status_code=status.HTTP_201_CREATED)
async def send_follow_request(
    user_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Send a follow request to a user (for private accounts) or auto-follow if public."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = await _get_user_or_404(db, user_id)

    # Check if user is public → auto-accept, just follow
    if not getattr(target, 'is_private', False):
        existing = await db.execute(
            select(Follow).where(and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id
            ))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Already following")

        follow = Follow(follower_id=current_user.id, following_id=user_id)
        db.add(follow)
        await db.flush()

        # Record activity
        await record_activity(
            db=db,
            user_id=user_id,
            actor_id=current_user.id,
            event_type="follow",
            target_type="user",
            target_id=user_id,
            metadata={"username": current_user.username},
        )
        return {"status": "following", "message": "Now following"}

    # Private account → send follow request
    existing_req = await db.execute(
        select(FollowRequest).where(and_(
            FollowRequest.from_user_id == current_user.id,
            FollowRequest.to_user_id == user_id,
            FollowRequest.status == "pending"
        ))
    )
    if existing_req.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Request already pending")

    existing = await db.execute(
        select(Follow).where(and_(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id
        ))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already following")

    req = FollowRequest(from_user_id=current_user.id, to_user_id=user_id)
    db.add(req)
    await db.flush()

    # Record activity
    await record_activity(
        db=db,
        user_id=user_id,
        actor_id=current_user.id,
        event_type="follow_request",
        target_type="user",
        target_id=user_id,
        metadata={"username": current_user.username},
    )
    return {"status": "pending", "message": "Request sent"}


@router.get("/me/follow-requests", response_model=FollowRequestListResponse)
async def get_my_follow_requests(
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Get pending follow requests directed to the current user."""
    result = await db.execute(
        select(FollowRequest)
        .options(selectinload(FollowRequest.from_user))
        .where(and_(
            FollowRequest.to_user_id == current_user.id,
            FollowRequest.status == "pending"
        ))
        .order_by(desc(FollowRequest.created_at))
    )
    reqs = result.scalars().all()

    items = []
    for r in reqs:
        u = r.from_user
        items.append(FollowRequestResponse(
            id=r.id,
            from_user_id=r.from_user_id,
            from_username=u.username if u else "unknown",
            from_display_name=getattr(u, 'display_name', None) if u else None,
            from_avatar=getattr(u, 'avatar_url', None) if u else None,
            created_at=r.created_at,
        ))

    count_result = await db.execute(
        select(func.count(FollowRequest.id)).where(and_(
            FollowRequest.to_user_id == current_user.id,
            FollowRequest.status == "pending"
        ))
    )
    total = count_result.scalar_one()

    return FollowRequestListResponse(items=items, total=total)


@router.post("/{user_id}/follow-request/{request_id}/accept", status_code=status.HTTP_200_OK)
async def accept_follow_request(
    user_id: UUID,
    request_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Accept a follow request from a user."""
    result = await db.execute(
        select(FollowRequest).where(and_(
            FollowRequest.id == request_id,
            FollowRequest.to_user_id == current_user.id,
            FollowRequest.from_user_id == user_id,
            FollowRequest.status == "pending"
        ))
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Create follow relationship
    follow = Follow(follower_id=user_id, following_id=current_user.id)
    db.add(follow)

    req.status = "accepted"
    req.updated_at = datetime.utcnow()
    await db.flush()

    # Record activity
    await record_activity(
        db=db,
        user_id=current_user.id,
        actor_id=user_id,
        event_type="follow",
        target_type="user",
        target_id=current_user.id,
        metadata={"username": current_user.username},
    )
    return {"status": "accepted", "message": "Follow request accepted"}


@router.post("/{user_id}/follow-request/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_follow_request(
    user_id: UUID,
    request_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Reject a follow request from a user."""
    result = await db.execute(
        select(FollowRequest).where(and_(
            FollowRequest.id == request_id,
            FollowRequest.to_user_id == current_user.id,
            FollowRequest.from_user_id == user_id,
            FollowRequest.status == "pending"
        ))
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "rejected"
    req.updated_at = datetime.utcnow()
    await db.flush()


@router.delete("/{user_id}/follow-request/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_follow_request(
    user_id: UUID,
    request_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Cancel a sent follow request (by the sender)."""
    result = await db.execute(
        select(FollowRequest).where(and_(
            FollowRequest.id == request_id,
            FollowRequest.from_user_id == current_user.id,
            FollowRequest.status == "pending"
        ))
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    await db.delete(req)
    await db.flush()


# ─── Followers / Following with status ──────────────────────────────────────

@router.get("/{user_id}/followers", response_model=FollowListResponse)
async def get_followers(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Get followers of a user. Use 'me' for current user's followers."""
    target_id = await _parse_user_id(user_id, current_user)

    count_result = await db.execute(
        select(func.count(Follow.id)).where(Follow.following_id == target_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Follow)
        .options(selectinload(Follow.follower))
        .where(Follow.following_id == target_id)
        .order_by(desc(Follow.created_at))
        .offset(offset)
        .limit(per_page)
    )
    follows = result.scalars().all()

    items = []
    for f in follows:
        u = f.follower
        status_info = await _get_follow_status_for_user(db, u.id, current_user)
        items.append(FollowUserResponse(
            user_id=u.id,
            username=u.username,
            display_name=getattr(u, 'display_name', None),
            avatar_url=getattr(u, 'avatar_url', None),
            is_following=status_info["is_following"],
            is_pending=status_info["is_pending"],
            created_at=f.created_at,
        ))

    return FollowListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.get("/{user_id}/following", response_model=FollowListResponse)
async def get_following(
    user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Get users that a user is following. Use 'me' for current user's following."""
    target_id = await _parse_user_id(user_id, current_user)

    count_result = await db.execute(
        select(func.count(Follow.id)).where(Follow.follower_id == target_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(Follow)
        .options(selectinload(Follow.following))
        .where(Follow.follower_id == target_id)
        .order_by(desc(Follow.created_at))
        .offset(offset)
        .limit(per_page)
    )
    follows = result.scalars().all()

    items = []
    for f in follows:
        u = f.following
        status_info = await _get_follow_status_for_user(db, u.id, current_user)
        items.append(FollowUserResponse(
            user_id=u.id,
            username=u.username,
            display_name=getattr(u, 'display_name', None),
            avatar_url=getattr(u, 'avatar_url', None),
            is_following=status_info["is_following"],
            is_pending=status_info["is_pending"],
            created_at=f.created_at,
        ))

    return FollowListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page > 0 else 0,
    )


@router.get("/{user_id}/follow-status", response_model=dict)
async def get_follow_status(
    user_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Get current user's follow status regarding another user."""
    status_info = await _get_follow_status_for_user(db, user_id, current_user)
    return {
        "user_id": str(user_id),
        "is_following": status_info["is_following"],
        "is_pending": status_info["is_pending"],
    }


@router.delete("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    user_id: UUID,
    db=Depends(get_db),
    *,
    current_user: CurrentUser,
):
    """Unfollow a user or cancel a pending follow request."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot unfollow yourself")

    # Delete follow relationship if exists
    result = await db.execute(
        select(Follow).where(and_(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id
        ))
    )
    follow_record = result.scalar_one_or_none()
    if follow_record:
        await db.delete(follow_record)
        await db.flush()
        return {"status": "unfollowed"}

    # Check for pending follow request
    result2 = await db.execute(
        select(FollowRequest).where(and_(
            FollowRequest.from_user_id == current_user.id,
            FollowRequest.to_user_id == user_id,
            FollowRequest.status == "pending"
        ))
    )
    req_record = result2.scalar_one_or_none()
    if req_record:
        await db.delete(req_record)
        await db.flush()
        return {"status": "request_cancelled"}

    raise HTTPException(status_code=404, detail="Not following or no pending request")

"""Reviews router for CRUD operations on reviews."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import CurrentUser
from app.models import Review, ReviewVote, User, VoteType
from app.services.notification_service import notify_review_liked
from app.schemas.review import (
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
    ReviewUpdate,
    ReviewVoteCreate,
    ReviewVoteResponse,
    ReviewSortBy,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    data: ReviewCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new review for a movie or TV show."""
    # Check if review already exists for this user + media
    existing = await db.execute(
        select(Review).where(
            and_(
                Review.user_id == current_user.id,
                Review.tmdb_id == data.tmdb_id,
                Review.media_type == data.media_type.value,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this item",
        )

    review = Review(
        user_id=current_user.id,
        tmdb_id=data.tmdb_id,
        media_type=data.media_type.value,
        rating=data.rating,
        content=data.content,
        is_spoiler=data.is_spoiler,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    # Update user stats: reviews_count +1
    await _update_user_stats_count(db, current_user.id, "reviews", +1)

    # Load user relationship for response
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
        .where(Review.id == review.id)
    )
    review = result.scalar_one()

    return review


@router.get("/media/{tmdb_id}/{media_type}", response_model=ReviewListResponse)
async def get_reviews_for_media(
    tmdb_id: int,
    media_type: str,
    sort_by: ReviewSortBy = Query(default=ReviewSortBy.RECENT, description="Sort order"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all public reviews for a specific movie or TV show."""
    # Build base query
    base_query = select(Review).options(selectinload(Review.user)).where(
        and_(Review.tmdb_id == tmdb_id, Review.media_type == media_type)
    )

    # Count total
    count_query = select(func.count(Review.id)).where(
        and_(Review.tmdb_id == tmdb_id, Review.media_type == media_type)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    if sort_by == ReviewSortBy.TOP_RATED:
        base_query = base_query.order_by(Review.rating.desc())
    elif sort_by == ReviewSortBy.MOST_USEFUL:
        base_query = base_query.order_by(Review.likes_count.desc())
    else:  # RECENT
        base_query = base_query.order_by(Review.created_at.desc())

    # Apply pagination
    offset = (page - 1) * per_page
    base_query = base_query.offset(offset).limit(per_page)

    result = await db.execute(base_query)
    items = result.scalars().all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/user/{user_id}", response_model=ReviewListResponse)
async def get_reviews_by_user(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all reviews by a specific user."""
    # Count total
    count_query = select(func.count(Review.id)).where(Review.user_id == user_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get reviews sorted by most recent
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
        .where(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items = result.scalars().all()

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single review by ID."""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update own review."""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
        .where(and_(Review.id == review_id, Review.user_id == current_user.id))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if data.rating is not None:
        review.rating = data.rating
    if data.content is not None:
        review.content = data.content
    if data.is_spoiler is not None:
        review.is_spoiler = data.is_spoiler

    await db.flush()
    await db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete own review."""
    result = await db.execute(
        select(Review).where(
            and_(Review.id == review_id, Review.user_id == current_user.id)
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    await db.delete(review)
    await db.flush()

    # Update user stats: reviews_count -1
    await _update_user_stats_count(db, current_user.id, "reviews", -1)


@router.post("/{review_id}/vote", response_model=ReviewVoteResponse)
async def vote_review(
    review_id: UUID,
    data: ReviewVoteCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Vote on a review (useful or not_useful). Voting again changes the vote."""
    # Get the review
    review_result = await db.execute(select(Review).where(Review.id == review_id))
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if review.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot vote on your own review",
        )

    # Check existing vote
    existing_vote = await db.execute(
        select(ReviewVote).where(
            and_(
                ReviewVote.review_id == review_id,
                ReviewVote.user_id == current_user.id,
            )
        )
    )
    vote = existing_vote.scalar_one_or_none()

    old_vote_type = vote.vote_type if vote else None
    new_vote_type = VoteType(data.vote_type.value)

    if vote:
        if vote.vote_type == new_vote_type:
            # Toggle off — remove vote
            await db.delete(vote)
            # Adjust likes count
            if new_vote_type == VoteType.USEFUL:
                review.likes_count = max(0, review.likes_count - 1)
        else:
            # Change vote type
            vote.vote_type = new_vote_type
            # Adjust likes count: remove old, add new
            if old_vote_type == VoteType.USEFUL:
                review.likes_count = max(0, review.likes_count - 1)
            if new_vote_type == VoteType.USEFUL:
                review.likes_count += 1
    else:
        # New vote
        vote = ReviewVote(
            user_id=current_user.id,
            review_id=review_id,
            vote_type=new_vote_type,
        )
        db.add(vote)
        if new_vote_type == VoteType.USEFUL:
            review.likes_count += 1

    await db.flush()
    await db.refresh(review)

    # Notify review owner (only on useful vote, not own review)
    if review.user_id != current_user.id and new_vote_type == VoteType.USEFUL:
        # Get review owner username for notification data
        owner_result = await db.execute(select(User).where(User.id == review.user_id))
        owner = owner_result.scalar_one_or_none()
        if owner:
            await notify_review_liked(
                db,
                review_owner_id=str(review.user_id),
                liker_username=current_user.username,
                tmdb_id=review.tmdb_id,
                media_type=review.media_type,
                review_id=review.id,
            )

    return ReviewVoteResponse(
        review_id=review.id,
        vote_type=data.vote_type,
        likes_count=review.likes_count,
    )


# --- Helper functions ---

async def _update_user_stats_count(
    db: AsyncSession, user_id: UUID, field: str, delta: int
):
    """Increment or decrement a user stats counter."""
    from app.models import UserStats

    result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = result.scalar_one_or_none()

    if not stats:
        # Create stats record if it doesn't exist
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    if hasattr(stats, f"{field}_count"):
        current = getattr(stats, f"{field}_count") or 0
        setattr(stats, f"{field}_count", max(0, current + delta))

    await db.flush()

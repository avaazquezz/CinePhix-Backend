"""Review model for user reviews with ratings."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MediaType


class Review(Base):
    """Movie or TV review with 1-5 star rating."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_user_media_review"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tmdb_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    media_type: Mapped[MediaType] = mapped_column(
        SQLEnum(MediaType),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_spoiler: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    likes_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews", lazy="joined")
    votes: Mapped[list["ReviewVote"]] = relationship(
        "ReviewVote",
        back_populates="review",
        cascade="all, delete-orphan",
    )


# Import User at bottom to avoid circular imports
from app.models.user import User
from app.models.review_vote import ReviewVote

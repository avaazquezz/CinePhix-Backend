"""ReviewVote model for useful/not_useful votes on reviews."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
import enum


class VoteType(str, enum.Enum):
    """Type of vote on a review."""

    USEFUL = "useful"
    NOT_USEFUL = "not_useful"


class ReviewVote(Base):
    """User vote (useful/not_useful) on a review."""

    __tablename__ = "review_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uq_user_review_vote"),
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
    review_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vote_type: Mapped[VoteType] = mapped_column(
        SQLEnum(VoteType),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="votes")


from app.models.review import Review

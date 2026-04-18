"""UserStats model for denormalized user statistics."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserStats(Base):
    """Denormalized counters for a user's activity stats."""

    __tablename__ = "user_stats"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    reviews_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    followers_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    following_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    lists_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    watchlist_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    favorites_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="stats")


from app.models.user import User

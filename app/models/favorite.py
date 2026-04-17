"""Favorite model for user likes."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.Enum import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class MediaType(str, enum.Enum):
    """Type of media item."""

    MOVIE = "movie"
    TV = "tv"


class Favorite(Base):
    """Movie or TV show marked as favorite by user."""

    __tablename__ = "favorites"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
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
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="favorites")

    __table_args__ = (
        # Unique constraint: user can't favorite same item twice
        {"schema": None},
    )


# Import User at bottom to avoid circular imports
from app.models.user import User
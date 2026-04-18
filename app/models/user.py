"""User model with authentication and profile data."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Registered user with email/password or OAuth authentication."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    is_pro: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    # OAuth provider (google, github, None for email/password)
    oauth_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    oauth_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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
    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="WatchlistItem.position",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    stats: Mapped["UserStats"] = relationship(
        "UserStats",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    pro_account: Mapped["UserPro"] = relationship(
        "UserPro",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    followers: Mapped[list["UserFollow"]] = relationship(
        "UserFollow",
        foreign_keys="UserFollow.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
    )
    following: Mapped[list["UserFollow"]] = relationship(
        "UserFollow",
        foreign_keys="UserFollow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    lists: Mapped[list["List"]] = relationship(
        "List",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["ActivityFeed"]] = relationship(
        "ActivityFeed",
        foreign_keys="ActivityFeed.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserPreferences(Base):
    """User preferences stored as JSONB for flexibility."""

    __tablename__ = "user_preferences"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # JSONB columns for preferences
    favorite_genres: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    preferred_decade: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    exclude_genres: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    min_rating: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )
    # Arbitrary extra preferences as JSONB
    extra: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
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
    user: Mapped["User"] = relationship("User", back_populates="preferences")


class RefreshToken(Base):
    """Refresh tokens for JWT authentication."""

    __tablename__ = "refresh_tokens"

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
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class MagicLink(Base):
    """Magic link tokens for passwordless email authentication."""

    __tablename__ = "magic_links"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


# Import these at bottom to avoid circular imports
from app.models.watchlist import WatchlistItem
from app.models.favorite import Favorite
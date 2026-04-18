"""User watched history and progress tracking model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WatchedHistory(Base):
    __tablename__ = "watched_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    tmdb_id: Mapped[int] = mapped_column(nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(nullable=False)  # 'movie' or 'tv'
    watched_at: Mapped[datetime] = mapped_column(nullable=False)
    progress_seconds: Mapped[int] = mapped_column(default=0)
    duration_seconds: Mapped[int | None] = mapped_column(default=None)
    completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
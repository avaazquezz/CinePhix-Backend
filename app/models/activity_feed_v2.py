"""Enhanced Activity Feed v2 — real-time activity with WebSocket support."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ActivityFeedV2(Base):
    __tablename__ = "activity_feed_v2"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(30), nullable=False)  # follow | like | comment | review | list | watch
    target_type = Column(String(30), nullable=True)   # review | list | comment | movie | tv
    target_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    event_metadata = Column('metadata', JSONB, nullable=True, default=dict)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    actor = relationship("User", foreign_keys=[actor_id], lazy="selectin")

    __table_args__ = (
        Index("ix_activity_feed_v2_user_created", "user_id", "created_at"),
        Index("ix_activity_feed_v2_user_unread", "user_id", "is_read"),
    )

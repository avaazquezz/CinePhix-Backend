from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ActivityFeed(Base):
    __tablename__ = "activity_feed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(30), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=False)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("idx_activity_user", "user_id", "created_at"),
        Index("idx_activity_public", "activity_type", "created_at"),
    )

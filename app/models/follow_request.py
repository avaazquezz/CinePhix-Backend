"""Follow requests model — for private account follow requests."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class FollowRequest(Base):
    __tablename__ = "follow_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    from_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    from_user = relationship("User", foreign_keys=[from_user_id], lazy="selectin")
    to_user = relationship("User", foreign_keys=[to_user_id], lazy="selectin")

    @property
    def is_pending(self):
        return self.status == "pending"



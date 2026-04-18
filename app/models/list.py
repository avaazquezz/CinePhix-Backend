from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class List(Base):
    __tablename__ = "lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    cover_image = Column(Text, nullable=True)
    items_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="lists")
    items = relationship("ListItem", back_populates="list", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_list_user_name"),
        CheckConstraint("char_length(name) >= 1", name="ck_list_name_not_empty"),
    )

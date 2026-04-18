from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ListItem(Base):
    __tablename__ = "list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("lists.id", ondelete="CASCADE"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)
    position = Column(Integer, default=0)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    list = relationship("List", back_populates="items")

    __table_args__ = (
        UniqueConstraint("list_id", "tmdb_id", "media_type", name="uq_list_item"),
        CheckConstraint("media_type IN ('movie', 'tv')", name="ck_list_item_media_type"),
    )

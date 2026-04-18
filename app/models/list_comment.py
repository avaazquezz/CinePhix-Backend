"""List comments model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, text

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ListComment(Base):
    __tablename__ = "list_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('gen_random_uuid()'))
    list_id: Mapped[int] = mapped_column(
        ForeignKey("lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(default=None)

    user: Mapped["User"] = relationship("User", lazy="joined")
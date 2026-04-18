from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserPro(Base):
    """Pro subscription status per user — created on Stripe subscription checkout success."""

    __tablename__ = "user_pro"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plan_type: Mapped[str] = mapped_column(String(20), nullable=False, default="pro")
    stripe_session_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pro_account")

    @property
    def is_active(self) -> bool:
        return self.expires_at > datetime.now(timezone.utc)

"""Add stripe_subscription_id to user_pro table for recurring billing."""

from alembic import op
import sqlalchemy as sa

revision = '010_stripe_subscription_id'
down_revision = '009_schema_catchup'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE user_pro ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(200)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE user_pro DROP COLUMN IF EXISTS stripe_subscription_id"))

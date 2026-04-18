"""Add stripe_subscription_id to user_pro table for recurring billing."""

from alembic import op
import sqlalchemy as sa

revision = '010_stripe_subscription_id'
down_revision = '009_follow_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'user_pro',
        sa.Column('stripe_subscription_id', sa.String(200), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_pro', 'stripe_subscription_id')

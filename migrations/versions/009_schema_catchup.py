"""Catch-up: users.bio (idempotent) + user_pro table if missing.

Fixes DBs that never ran 003 or were created without Alembic while the ORM expects bio.
"""
from alembic import op
import sqlalchemy as sa

revision = "009_schema_catchup"
down_revision = "006_review_comments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT"))
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_pro (
                user_id UUID NOT NULL PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                plan_type VARCHAR(20) NOT NULL DEFAULT 'pro',
                stripe_session_id VARCHAR(200),
                granted_at TIMESTAMPTZ NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS user_pro"))
    op.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS bio"))

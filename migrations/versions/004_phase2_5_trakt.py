"""Phase 2.5 Step 3: Trakt.tv integration — add trakt_connections table"""
from alembic import op
import sqlalchemy as sa

revision = "004_phase2_5_trakt"
down_revision = "003_phase2_5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trakt_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("trakt_connections")

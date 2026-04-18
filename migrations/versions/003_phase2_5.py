"""Phase 2.5: Add bio field to users table + user_pro table"""
from alembic import op
import sqlalchemy as sa

revision = "003_phase2_5"
down_revision = "002_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add bio column to users table
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "bio")

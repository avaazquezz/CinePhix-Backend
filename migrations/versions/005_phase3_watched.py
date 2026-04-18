"""Phase 3: watched history + progress tracking.

Revision ID: 005
Revises: 004_phase2_5_trakt
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '005_phase3_watched'
down_revision = '004_phase2_5_trakt'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'watched_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=False, index=True),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('watched_at', sa.DateTime(), nullable=False),
        sa.Column('progress_seconds', sa.Integer(), default=0),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('completed', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    # Composite index for lookups
    op.create_index('ix_watched_user_media', 'watched_history', ['user_id', 'tmdb_id', 'media_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_watched_user_media', table_name='watched_history')
    op.drop_table('watched_history')
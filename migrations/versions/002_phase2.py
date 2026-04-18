"""Phase 2 migration - Lists, ListItems, ActivityFeed

Revision ID: 002_phase2
Revises: 001_initial
Create Date: 2026-04-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_phase2'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lists table
    op.create_table(
        'lists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=True),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('cover_image', sa.Text(), nullable=True),
        sa.Column('items_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'name', name='uq_list_user_name'),
    )
    op.create_index('idx_lists_user', 'lists', ['user_id'])
    op.create_index('idx_lists_public', 'lists', ['is_public', 'is_featured'])

    # Create list_items table
    op.create_table(
        'list_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('list_id', sa.Integer(), sa.ForeignKey('lists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(10), nullable=False),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('list_id', 'tmdb_id', 'media_type', name='uq_list_item'),
        sa.CheckConstraint("media_type IN ('movie', 'tv')", name='ck_list_item_media_type'),
    )
    op.create_index('idx_list_items_list', 'list_items', ['list_id'])

    # Create activity_feed table
    op.create_table(
        'activity_feed',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_type', sa.String(30), nullable=False),
        sa.Column('target_type', sa.String(20), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_activity_user', 'activity_feed', ['user_id', 'created_at'])
    op.create_index('idx_activity_public', 'activity_feed', ['activity_type', 'created_at'])

    # Add lists_count to user_stats if not exists
    # (UserStats table already exists, we just need to check via direct SQL if column exists)


def downgrade() -> None:
    op.drop_table('activity_feed')
    op.drop_table('list_items')
    op.drop_table('lists')

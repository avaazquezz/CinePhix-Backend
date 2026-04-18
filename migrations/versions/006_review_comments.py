"""Review comments table for review-level comments.

Revision ID: 006_review_comments
Revises: 005_phase3_watched
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '006_review_comments'
down_revision = '005_phase3_watched'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'review_comments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('review_id', UUID(as_uuid=True), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('review_comments')

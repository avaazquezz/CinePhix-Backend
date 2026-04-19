"""Review comments + reviews + review_votes tables.

Revision ID: 006_review_comments
Revises: 005_phase3_watched
Create Date: 2026-04-18

Note: reviews and review_votes tables were missed in the original migration chain.
This migration creates them (IF NOT EXISTS for safety) before creating review_comments.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006_review_comments"
down_revision = "005_phase3_watched"
branch_labels = None
depends_on = None


def upgrade():
    # Create reviews table (if not exists — handles DBs created without this migration)
    op.execute(
        sa.text("""
            CREATE TABLE IF NOT EXISTS reviews (
                id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                tmdb_id INTEGER NOT NULL,
                media_type VARCHAR(10) NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                content TEXT NOT NULL DEFAULT '',
                is_spoiler BOOLEAN NOT NULL DEFAULT FALSE,
                likes_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_user_media_review UNIQUE (user_id, tmdb_id, media_type)
            )
        """)
    )
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"], if_not_exists=True)
    op.create_index("ix_reviews_tmdb_id", "reviews", ["tmdb_id"], if_not_exists=True)

    # Create review_votes table
    op.execute(
        sa.text("""
            CREATE TABLE IF NOT EXISTS review_votes (
                id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
                review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                vote_type VARCHAR(20) NOT NULL CHECK (vote_type IN ('useful', 'not_useful')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_review_vote UNIQUE (review_id, user_id)
            )
        """)
    )
    op.create_index("ix_review_votes_review_id", "review_votes", ["review_id"], if_not_exists=True)
    op.create_index("ix_review_votes_user_id", "review_votes", ["user_id"], if_not_exists=True)

    # Create list_items table (if not exists — missed in 002_phase2)
    op.execute(
        sa.text("""
            CREATE TABLE IF NOT EXISTS list_items (
                id SERIAL PRIMARY KEY,
                list_id INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
                tmdb_id INTEGER NOT NULL,
                media_type VARCHAR(10) NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_list_item UNIQUE (list_id, tmdb_id, media_type)
            )
        """)
    )
    op.create_index("ix_list_items_list_id", "list_items", ["list_id"], if_not_exists=True)

    # Create review_comments table
    op.create_table(
        "review_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("review_comments")
    op.execute(sa.text("DROP TABLE IF EXISTS review_votes"))
    op.execute(sa.text("DROP TABLE IF EXISTS reviews"))
    op.execute(sa.text("DROP TABLE IF EXISTS list_items"))

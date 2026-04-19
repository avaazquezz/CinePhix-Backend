"""
Catch-up: add missing DB columns that exist in ORM models but were never migrated.

- activity_feed.extra_data (was 'metadata' in migration 002)
- lists.collaborators (never in any migration)
- lists.updated_at (referenced but missing)
- media_type enum for reviews/watchlist/favorites tables
"""
from alembic import op
import sqlalchemy as sa

revision = "011_missing_columns"
down_revision = "010_stripe_subscription_id"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure mediatype enum exists (created by watchlist migration 001 on old DBs,
    # but reviews table on this fresh DB used VARCHAR — fix that mismatch)
    op.execute(
        sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mediatype') THEN
                    CREATE TYPE mediatype AS ENUM ('MOVIE', 'TV');
                END IF;
            END $$;
        """)
    )

    # activity_feed: rename metadata -> extra_data or add extra_data
    op.execute(
        sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'activity_feed' AND column_name = 'extra_data'
                ) THEN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'activity_feed' AND column_name = 'metadata'
                    ) THEN
                        ALTER TABLE activity_feed RENAME COLUMN metadata TO extra_data;
                    ELSE
                        ALTER TABLE activity_feed ADD COLUMN extra_data JSONB DEFAULT '{}'::jsonb NOT NULL;
                    END IF;
                END IF;
            END $$;
        """)
    )

    # lists: add collaborators
    op.execute(
        sa.text(
            "ALTER TABLE lists ADD COLUMN IF NOT EXISTS collaborators JSONB DEFAULT '[]'::jsonb NOT NULL"
        )
    )

    # lists: ensure updated_at exists
    op.execute(
        sa.text(
            "ALTER TABLE lists ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL"
        )
    )

    # reviews.media_type: convert from VARCHAR to mediatype enum
    op.execute(
        sa.text(
            "ALTER TABLE reviews ALTER COLUMN media_type TYPE mediatype USING media_type::mediatype"
        )
    )

    # watchlist_items.media_type: ensure it uses mediatype
    op.execute(
        sa.text(
            "ALTER TABLE watchlist_items ALTER COLUMN media_type TYPE mediatype USING media_type::mediatype"
        )
    )

    # favorites.media_type: same
    op.execute(
        sa.text(
            "ALTER TABLE favorites ALTER COLUMN media_type TYPE mediatype USING media_type::mediatype"
        )
    )


def downgrade():
    op.execute(sa.text("ALTER TABLE lists DROP COLUMN IF EXISTS collaborators"))
    op.execute(sa.text("ALTER TABLE lists DROP COLUMN IF EXISTS updated_at"))
    op.execute(
        sa.text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'activity_feed' AND column_name = 'extra_data'
                ) THEN
                    ALTER TABLE activity_feed RENAME COLUMN extra_data TO metadata;
                END IF;
            END $$;
        """)
    )
    op.execute(sa.text("ALTER TABLE reviews ALTER COLUMN media_type TYPE VARCHAR(10)"))
    op.execute(sa.text("ALTER TABLE watchlist_items ALTER COLUMN media_type TYPE VARCHAR(10)"))
    op.execute(sa.text("ALTER TABLE favorites ALTER COLUMN media_type TYPE VARCHAR(10)"))
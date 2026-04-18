#!/usr/bin/env python3
"""
Legacy Docker / dev DBs: schema was created without Alembic, so `alembic_version` is missing
while `public.users` already exists. `alembic upgrade head` would re-run 001_initial and fail
with DuplicateTable. In that case we stamp the last revision before catch-up migrations so
only 009+ apply.

If your DB is missing migrations after 006, fix manually (dump + restore or targeted SQL).
"""
from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Last linear revision before 009_schema_catchup (see migrations/versions/).
BASELINE_REVISION = "006_review_comments"


def _sync_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ensure_alembic_baseline: DATABASE_URL not set; skipping", file=sys.stderr)
        sys.exit(0)
    if "+asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


def main() -> None:
    url = _sync_url()
    engine = create_engine(url, poolclass=NullPool)
    with engine.connect() as conn:
        has_users = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'users')"
            )
        ).scalar()
        if not has_users:
            return

        has_av = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version')"
            )
        ).scalar()
        if has_av:
            row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            if row and row[0]:
                return

    print(
        f"ensure_alembic_baseline: public.users exists but Alembic has no revision; "
        f"stamping {BASELINE_REVISION} (then upgrade will apply 009+).",
        file=sys.stderr,
    )
    subprocess.run(
        ["alembic", "stamp", BASELINE_REVISION],
        cwd="/app",
        check=True,
    )


if __name__ == "__main__":
    main()

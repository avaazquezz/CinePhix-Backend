#!/bin/sh
set -e
cd /app
python3 scripts/ensure_alembic_baseline.py
alembic upgrade head
exec uvicorn app:app --host 0.0.0.0 --port 8000

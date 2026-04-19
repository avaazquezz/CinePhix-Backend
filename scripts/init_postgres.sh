#!/bin/bash
# Ensure postgres user has the configured password on every container start.
# Handles the case where the data volume persisted from a previous run
# with a different (or null) password.

set -e

# Wait for postgres to be ready
until psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 1
done

# Set the password (idempotent — safe to run on every start)
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';" 2>/dev/null \
    || psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c \
    "ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"

echo "PostgreSQL password ensured."

#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
        echo "PostgreSQL is ready."
        break
    fi
    echo "Attempt $i/30..."
    sleep 1
done

# Fix password on every start (handles password drift from old volume data)
echo "Ensuring postgres user password is correct..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';" 2>/dev/null \
    || PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d postgres -c \
    "ALTER USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';" 2>/dev/null \
    || echo "Password fix skipped (DB may not be fully ready yet)."

echo "Starting PostgreSQL..."
exec docker-entrypoint.sh "$@"

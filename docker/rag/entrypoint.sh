#!/bin/sh
set -e

if [ "$1" = "uvicorn" ]; then
    echo "Running database migrations..."
    alembic -c /app/models/db_schemes/rag_db/alembic.ini upgrade head
fi

echo "Starting application..."

exec "$@"
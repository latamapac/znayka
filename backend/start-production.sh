#!/bin/bash
set -e

echo "=== ZNAYKA - Production Startup ==="

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

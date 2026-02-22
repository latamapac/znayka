#!/bin/bash
set -e

echo "=== ZNAYKA - Production Startup ==="
echo "Database: ${DATABASE_URL:0:40}..."

# Skip migrations in production (run manually if needed)
# alembic upgrade head

# Start the application immediately
echo "Starting application server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1

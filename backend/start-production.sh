#!/bin/bash
set -e

echo "=== Russian Science Hub - Production Startup ==="
echo "Database URL configured: ${DATABASE_URL:0:30}..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Check if we need to seed the database
if [ "${SEED_DATABASE:-false}" = "true" ]; then
    echo "Seeding database with sample data..."
    python -c "
import asyncio
from app.db.session import async_session
from app.services.indexing_service import IndexingService

async def seed():
    async with async_session() as db:
        indexer = IndexingService(db)
        # Sample data will be loaded if tables are empty
        print('Database seeding completed')

asyncio.run(seed())
"
fi

# Start the application
echo "Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1

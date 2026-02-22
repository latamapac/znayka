#!/bin/bash

# Switch between SQLite and PostgreSQL databases
# Usage: ./switch-db.sh [sqlite|postgres]

set -e

DB_TYPE=${1:-sqlite}

echo "🔄 Switching to $DB_TYPE..."

cd backend

if [ "$DB_TYPE" = "sqlite" ]; then
    echo "Setting up SQLite..."
    cat > .env << 'EOF'
USE_SQLITE=true
DATABASE_URL=sqlite+aiosqlite:///./russia_science_hub.db
SECRET_KEY=local-dev-key
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
PORT=8000
EOF
    echo "✅ SQLite configured"
    echo "Database file: backend/russia_science_hub.db"

elif [ "$DB_TYPE" = "postgres" ]; then
    echo "Setting up PostgreSQL..."
    
    # Check if PostgreSQL is running
    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "❌ PostgreSQL not running on localhost:5432"
        echo "Start PostgreSQL first:"
        echo "  brew services start postgresql@15  (Mac)"
        echo "  sudo systemctl start postgresql     (Linux)"
        exit 1
    fi
    
    # Check if pgvector is installed
    if ! psql -U postgres -d postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';" | grep -q vector; then
        echo "⚠️  pgvector not installed"
        echo "Install: brew install pgvector  (Mac)"
        echo "        sudo apt install postgresql-15-pgvector  (Linux)"
        exit 1
    fi
    
    # Create database if not exists
    psql -U postgres -c "CREATE DATABASE russia_science_hub;" 2>/dev/null || echo "Database may already exist"
    psql -U postgres -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS vector;"
    
    cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/russia_science_hub
SECRET_KEY=local-dev-key-min-32-characters-long
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
PORT=8000
EOF
    
    echo "✅ PostgreSQL configured"
    echo "Creating tables..."
    unset USE_SQLITE
    python3 -c "
import asyncio
from app.db.base import init_db
asyncio.run(init_db())
print('✅ Tables created')
"
else
    echo "Usage: ./switch-db.sh [sqlite|postgres]"
    exit 1
fi

echo ""
echo "Current configuration:"
cat .env | grep -E "^(USE_SQLITE|DATABASE_URL)"

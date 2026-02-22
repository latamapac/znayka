#!/bin/bash

# Simple startup script for Russian Science Hub
# No Docker required - uses SQLite

set -e

echo "🚀 Russian Science Hub - Quick Start"
echo "====================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -n "$BACKEND_PID" ]; then kill $BACKEND_PID 2>/dev/null || true; fi
    if [ -n "$FRONTEND_PID" ]; then kill $FRONTEND_PID 2>/dev/null || true; fi
    exit 0
}
trap cleanup INT TERM

# Backend setup
echo "📦 Setting up Backend..."
cd backend

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install minimal dependencies
echo "Installing dependencies..."
pip install -q fastapi uvicorn sqlalchemy aiosqlite python-dotenv pydantic pydantic-settings

# Create .env for SQLite
if [ ! -f ".env" ]; then
    echo "Creating .env configuration..."
    cat > .env << 'EOF'
USE_SQLITE=true
DATABASE_URL=sqlite+aiosqlite:///./russia_science_hub.db
SECRET_KEY=local-dev-key-change-in-production
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
PROJECT_VERSION=0.1.0
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
EOF
fi

# Create __init__.py files if missing
touch app/__init__.py
touch app/api/__init__.py
touch app/core/__init__.py
touch app/db/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py

# Initialize database (create tables)
echo "Initializing database..."
python3 << 'PYEOF'
import asyncio
import sys
sys.path.insert(0, '.')

from app.db.base import init_db

async def main():
    await init_db()
    print("Database initialized!")

asyncio.run(main())
PYEOF

echo -e "${GREEN}✓ Backend ready${NC}"

# Start backend
echo ""
echo "🔥 Starting Backend: http://localhost:8000"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

# Frontend setup
echo ""
echo "📦 Setting up Frontend..."
cd frontend

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
fi

# Create .env for frontend
if [ ! -f ".env" ]; then
    echo "VITE_API_URL=http://localhost:8000/api/v1" > .env
fi

echo -e "${GREEN}✓ Frontend ready${NC}"

# Start frontend
echo ""
echo "🎨 Starting Frontend: http://localhost:5173"
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo -e "${GREEN}✅ All services running!${NC}"
echo "=========================================="
echo ""
echo "🌐 Frontend:    http://localhost:5173"
echo "🔌 Backend:     http://localhost:8000"
echo "📚 API Docs:    http://localhost:8000/docs"
echo "💾 Database:    backend/russia_science_hub.db (SQLite)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait
wait

#!/bin/bash

# Russian Science Hub - Working Startup Script
# Run this to start both backend and frontend locally
# Usage: ./start.sh [backend_port] [frontend_port]
# Example: ./start.sh 8080 3000

set -e

# Default ports
BACKEND_PORT=${1:-8000}
FRONTEND_PORT=${2:-5173}

echo "🚀 Russian Science Hub - Startup"
echo "================================="
echo "Backend port: $BACKEND_PORT"
echo "Frontend port: $FRONTEND_PORT"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -n "$BACKEND_PID" ]; then kill $BACKEND_PID 2>/dev/null || true; fi
    if [ -n "$FRONTEND_PID" ]; then kill $FRONTEND_PID 2>/dev/null || true; fi
    exit 0
}
trap cleanup INT TERM

# Check Python
echo "Checking Python..."
python3 --version || (echo "❌ Python 3 not found"; exit 1)

# Check Node
echo "Checking Node.js..."
node --version || (echo "❌ Node.js not found"; exit 1)

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
python3 -m pip install -q fastapi uvicorn sqlalchemy aiosqlite greenlet \
    python-dotenv pydantic pydantic-settings beautifulsoup4 lxml aiohttp 2>/dev/null || true

# Backend setup
echo ""
echo "🔧 Setting up Backend..."
cd backend

# Create .env for SQLite
if [ ! -f ".env" ]; then
    echo "Creating backend/.env..."
    cat > .env << EOF
USE_SQLITE=true
DATABASE_URL=sqlite+aiosqlite:///./russia_science_hub.db
SECRET_KEY=local-dev-key
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
PROJECT_VERSION=0.1.0
CORS_ORIGINS=["http://localhost:$FRONTEND_PORT","http://localhost:3000","http://127.0.0.1:$FRONTEND_PORT"]
EMBEDDING_DIMENSION=384
PORT=$BACKEND_PORT
EOF
fi

# Initialize database
echo "Initializing database..."
python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, '.')
os.environ['USE_SQLITE'] = 'true'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./russia_science_hub.db'
os.environ['SECRET_KEY'] = 'test'

from app.db.base import init_db
import asyncio
asyncio.run(init_db())
print("✓ Database ready")
PYEOF

# Start backend
echo ""
echo "🔥 Starting Backend..."
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend PID: $BACKEND_PID${NC}"
echo "  → http://localhost:$BACKEND_PORT"
echo "  → API Docs: http://localhost:$BACKEND_PORT/docs"
cd ..

sleep 3

# Frontend setup
echo ""
echo "🔧 Setting up Frontend..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
fi

# Create .env for frontend
if [ ! -f ".env" ]; then
    echo "VITE_API_URL=http://localhost:$BACKEND_PORT/api/v1" > .env
fi

# Start frontend
echo ""
echo "🎨 Starting Frontend..."
npm run dev -- --host --port $FRONTEND_PORT > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend PID: $FRONTEND_PID${NC}"
echo "  → http://localhost:$FRONTEND_PORT"
cd ..

echo ""
echo "========================================"
echo -e "${GREEN}✅ All services running!${NC}"
echo "========================================"
echo ""
echo "🌐 Open http://localhost:$FRONTEND_PORT in your browser"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend/backend.log"
echo "  Frontend: tail -f frontend/frontend.log"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Wait
wait

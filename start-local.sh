#!/bin/bash

# Russian Science Hub - Local Startup Script (No Docker)
# This script starts the backend and frontend locally

set -e

echo "🚀 Starting Russian Science Hub locally..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup INT TERM EXIT

# Check PostgreSQL
echo "🔍 Checking PostgreSQL..."
if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL not detected on localhost:5432${NC}"
    echo "Options:"
    echo "  1. Install PostgreSQL: brew install postgresql@15 (Mac)"
    echo "  2. Use SQLite for testing (limited features)"
    echo "  3. Use Railway/Neon for remote PostgreSQL"
    echo ""
    read -p "Use SQLite for testing? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        export USE_SQLITE=true
        echo -e "${GREEN}✓ Will use SQLite (some features won't work)${NC}"
    else
        echo -e "${RED}❌ Cannot continue without database${NC}"
        exit 1
    fi
fi

# Setup Backend
echo ""
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install additional dependencies for SQLite mode if needed
if [ "$USE_SQLITE" = true ]; then
    pip install -q aiosqlite
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    if [ "$USE_SQLITE" = true ]; then
        cat > .env << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///./russia_science_hub.db
SECRET_KEY=local-development-key-change-in-production
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
EOF
    else
        cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/russia_science_hub
SECRET_KEY=local-development-key-change-in-production
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
EOF
    fi
fi

# Create database and run migrations
echo "Setting up database..."
if [ "$USE_SQLITE" != true ]; then
    # Try to create PostgreSQL database
    createdb russia_science_hub 2>/dev/null || echo "Database may already exist"
    psql -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo "pgvector extension may need to be installed"
fi

# Run migrations (skip for SQLite without Alembic support)
if [ "$USE_SQLITE" != true ]; then
    alembic upgrade head 2>/dev/null || echo "Migration may need pgvector"
fi

echo -e "${GREEN}✓ Backend ready${NC}"

# Start Backend
echo ""
echo "🔥 Starting Backend on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Setup Frontend
echo ""
echo "📦 Setting up Frontend..."
cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

echo -e "${GREEN}✓ Frontend ready${NC}"

# Start Frontend
echo ""
echo "🎨 Starting Frontend on http://localhost:5173"
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo -e "${GREEN}🎉 Russian Science Hub is running!${NC}"
echo "========================================"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔌 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
wait

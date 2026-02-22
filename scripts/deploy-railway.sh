#!/bin/bash

# Russian Science Hub - Railway Deployment Script
# Usage: ./scripts/deploy-railway.sh

set -e

echo "🚀 Deploying Russian Science Hub to Railway..."

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check login
if ! railway whoami &> /dev/null; then
    echo "🔑 Please login to Railway..."
    railway login
fi

echo ""
echo "📦 Step 1: Deploying Backend..."
cd backend

# Initialize project if not already
if [ ! -f ../.railway/project.json ]; then
    echo "Creating new Railway project..."
    railway init
fi

# Add PostgreSQL if not exists
echo "Checking PostgreSQL..."
railway add --database postgres || echo "PostgreSQL already exists"

# Deploy
railway up --detach

echo ""
echo "🗄️  Step 2: Running Database Migrations..."
railway run "alembic upgrade head" || echo "Migration may need to be run manually from Railway dashboard"

echo ""
echo "🎨 Step 3: Deploying Frontend..."
cd ../frontend

# Check if frontend service exists
if railway service list | grep -q "frontend"; then
    railway up --service frontend --detach
else
    echo "Creating frontend service..."
    railway init --service frontend
    railway up --detach
fi

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🌐 Your app is available at:"
railway domain

echo ""
echo "📊 Useful commands:"
echo "  - View logs: railway logs --follow"
echo "  - View status: railway status"
echo "  - Open dashboard: railway open"
echo ""
echo "⚠️  Don't forget to:"
echo "  1. Set OPENAI_API_KEY in Railway dashboard for embeddings"
echo "  2. Set SECRET_KEY for production"
echo "  3. Configure CORS_ORIGINS with your frontend URL"

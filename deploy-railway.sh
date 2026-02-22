#!/bin/bash
# Deploy Russian Science Hub to Railway - METADATA ONLY

set -e

echo "🚀 Russian Science Hub - Railway Deployment"
echo "=============================================="

# Check railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Install: npm install -g @railway/cli"
    exit 1
fi

echo ""
echo "1️⃣  Logging in to Railway..."
railway login

echo ""
echo "2️⃣  Initializing project..."
cd backend
railway init

echo ""
echo "3️⃣  Adding PostgreSQL database..."
railway add --database postgres

echo ""
echo "4️⃣  Setting environment variables..."
railway variables set USE_SQLITE=false
railway variables set USE_TEMPORAL=false
railway variables.set SEED_DATABASE=true

echo ""
echo "5️⃣  Deploying..."
railway up

echo ""
echo "6️⃣  Running migrations..."
railway run "alembic upgrade head"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  - Check status: railway status"
echo "  - View logs: railway logs"
echo "  - Open app: railway open"
echo ""
echo "After deploy, set SEED_DATABASE=false to avoid re-seeding:"
echo "  railway variables set SEED_DATABASE=false"

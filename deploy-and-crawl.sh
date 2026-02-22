#!/bin/bash
# Deploy Phase 2 (PDF features) and start crawling

set -e

export PROJECT_ID="znayka-fresh-1771794343"
export REGION="europe-north1"
export SERVICE_URL="https://znayka-674193695957.europe-north1.run.app"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🚀 DEPLOY PHASE 2 + CRAWL                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Build with PDF features
echo "🔨 Step 1: Building with PDF features..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka:full -f Dockerfile.full
echo "✅ Build complete"
echo ""

# Step 2: Deploy
echo "🚀 Step 2: Deploying..."
gcloud run deploy znayka \
  --image gcr.io/$PROJECT_ID/znayka:full \
  --region=$REGION \
  --memory=2Gi \
  --timeout=300
echo "✅ Deployed"
echo ""

# Step 3: Wait for service
echo "⏳ Step 3: Waiting for service..."
sleep 5

# Step 4: Test endpoints
echo "🧪 Step 4: Testing endpoints..."
curl -s $SERVICE_URL/health
echo ""
curl -s $SERVICE_URL/api/v1/sources/list | head -100
echo ""

# Step 5: Start crawling
echo "🕷️  Step 5: Starting crawlers..."

echo "  → Crawling arXiv (machine learning)..."
curl -s -X POST $SERVICE_URL/api/v1/worker/crawl \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "source": "arxiv", "limit": 50}'
echo ""

echo "  → Crawling CyberLeninka (AI)..."
curl -s -X POST $SERVICE_URL/api/v1/worker/crawl \
  -H "Content-Type: application/json" \
  -d '{"query": "искусственный интеллект", "source": "cyberleninka", "limit": 30}'
echo ""

echo "  → Crawling eLibrary (data science)..."
curl -s -X POST $SERVICE_URL/api/v1/worker/crawl \
  -H "Content-Type: application/json" \
  -d '{"query": "data science", "source": "elibrary", "limit": 30}'
echo ""

echo "✅ Crawl jobs started!"
echo ""

# Step 6: Show status
echo "📊 Step 6: Current stats..."
curl -s $SERVICE_URL/api/v1/analytics/stats
echo ""

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🎉 DONE!                                                  ║"
echo "║                                                            ║"
echo "║  URL: $SERVICE_URL"
echo "║                                                            ║"
echo "║  Crawlers are running in background.                       ║"
echo "║  Check stats with: curl $SERVICE_URL/api/v1/analytics/stats"
echo "╚════════════════════════════════════════════════════════════╝"

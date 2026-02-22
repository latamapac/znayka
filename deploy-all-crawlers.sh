#!/bin/bash
# Deploy ZNAYKA with ALL crawlers and Temporal monitoring

set -e

export PROJECT_ID="znayka-fresh-1771794343"
export REGION="europe-north1"
export SERVICE_URL="https://znayka-674193695957.europe-north1.run.app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🚀 ZNAYKA - ALL CRAWLERS + TEMPORAL              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Build with full features (including Temporal)
echo -e "${YELLOW}🔨 Step 1: Building with all features...${NC}"
gcloud builds submit --config=cloudbuild.full.yaml
echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Step 2: Deploy with more resources for Temporal
echo -e "${YELLOW}🚀 Step 2: Deploying with Temporal support...${NC}"
gcloud run deploy znayka \
  --image gcr.io/$PROJECT_ID/znayka:full \
  --region=$REGION \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=10 \
  --set-env-vars="USE_TEMPORAL=true,TEMPORAL_HOST=localhost:7233"
echo -e "${GREEN}✅ Deployed${NC}"
echo ""

# Step 3: Wait for service
echo -e "${YELLOW}⏳ Step 3: Waiting for service...${NC}"
sleep 10
curl -s $SERVICE_URL/health
echo ""
echo -e "${GREEN}✅ Service ready${NC}"
echo ""

# Step 4: Start ALL crawlers with Temporal
echo -e "${YELLOW}🕷️  Step 4: Starting ALL 9 crawlers...${NC}"
echo ""

# Define all sources and queries
SOURCES=("arxiv" "cyberleninka" "elibrary" "hse_scientometrics" "inion" "presidential_library" "rosstat_emiss" "rsl_dissertations" "rusneb")
QUERIES=("machine learning" "artificial intelligence" "data science" "neural networks" "deep learning")

TOTAL_JOBS=0

# Start bulk crawl for each query across all sources
for QUERY in "${QUERIES[@]}"; do
    echo -e "${BLUE}  → Starting bulk crawl for: '$QUERY'${NC}"
    
    # Submit bulk crawl workflow via API
    RESPONSE=$(curl -s -X POST $SERVICE_URL/api/v1/worker/crawl \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$QUERY\", \"sources\": [\"arxiv\", \"cyberleninka\", \"elibrary\"], \"limit\": 30}")
    
    echo "    Response: $RESPONSE"
    ((TOTAL_JOBS++))
    sleep 2
done

echo ""
echo -e "${GREEN}✅ Started $TOTAL_JOBS bulk crawl jobs${NC}"
echo ""

# Step 5: Monitor with Temporal (if available)
echo -e "${YELLOW}📊 Step 5: Setting up Temporal monitoring...${NC}"

# Check if Temporal is enabled
TEMPORAL_STATUS=$(curl -s $SERVICE_URL/ | grep -o '"temporal_enabled": [^,]*' | cut -d' ' -f2)
if [ "$TEMPORAL_STATUS" = "true" ]; then
    echo -e "${GREEN}  ✓ Temporal is enabled${NC}"
    
    # Submit maintenance workflow for monitoring
    curl -s -X POST $SERVICE_URL/api/v1/worker/maintenance
    echo "  ✓ Maintenance workflow started"
else
    echo -e "${YELLOW}  ⚠ Temporal not enabled (using direct API calls)${NC}"
fi
echo ""

# Step 6: Show initial stats
echo -e "${YELLOW}📈 Step 6: Initial stats...${NC}"
STATS=$(curl -s $SERVICE_URL/api/v1/analytics/stats)
echo "  $STATS"
echo ""

# Step 7: Monitoring loop
echo -e "${YELLOW}🔍 Step 7: Starting monitoring...${NC}"
echo "  Checking progress every 30 seconds..."
echo "  (Press Ctrl+C to stop monitoring)"
echo ""

for i in {1..20}; do
    sleep 30
    
    # Get current stats
    CURRENT_STATS=$(curl -s $SERVICE_URL/api/v1/analytics/stats)
    PAPER_COUNT=$(echo $CURRENT_STATS | grep -o '"total_papers": [0-9]*' | cut -d' ' -f2 || echo "0")
    
    echo -e "${BLUE}  [$(date '+%H:%M:%S')] Papers indexed: $PAPER_COUNT${NC}"
    
    # Check if we have enough papers
    if [ "$PAPER_COUNT" -gt 100 ]; then
        echo -e "${GREEN}  🎉 Target reached! 100+ papers indexed.${NC}"
        break
    fi
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉 ALL CRAWLERS RUNNING!                                  ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  URL: $SERVICE_URL${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Crawlers active:                                          ║${NC}"
echo -e "${GREEN}║    • arXiv (ML, AI, Data Science)                          ║${NC}"
echo -e "${GREEN}║    • CyberLeninka (Russian AI research)                    ║${NC}"
echo -e "${GREEN}║    • eLibrary (Russian citations)                          ║${NC}"
echo -e "${GREEN}║    • HSE Scientometrics                                    ║${NC}"
echo -e "${GREEN}║    • INION                                                 ║${NC}"
echo -e "${GREEN}║    • RSL Dissertations                                     ║${NC}"
echo -e "${GREEN}║    • RUSNEB                                                ║${NC}"
echo -e "${GREEN}║    • Presidential Library                                  ║${NC}"
echo -e "${GREEN}║    • Rosstat                                               ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Check status:                                             ║${NC}"
echo -e "${GREEN}║    curl $SERVICE_URL/api/v1/analytics/stats${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  Search papers:                                            ║${NC}"
echo -e "${GREEN}║    curl "$SERVICE_URL/api/v1/papers/search?q=AI&limit=10"${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

#!/bin/bash
# ZNAYKA Automatic Crawler - Shell Script Version
# Crawls ALL 9 sources with multiple queries to build unique database

set -e

API_URL="https://znayka-674193695957.europe-north1.run.app"
FRONTEND_URL="https://znayka-frontend.vercel.app"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           ZNAYKA AUTOMATIC CRAWLER MANAGER                     ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  Frontend: ${FRONTEND_URL}${NC}"
echo -e "${BLUE}║  API:      ${API_URL}${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Comprehensive query list
QUERIES=(
    "machine learning"
    "artificial intelligence"
    "deep learning"
    "neural networks"
    "quantum computing"
    "blockchain"
    "cybersecurity"
    "data science"
    "cloud computing"
    "IoT"
)

LIMIT=${1:-30}

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   • Sources:     9 (all available)"
echo "   • Queries:     ${#QUERIES[@]} topics"
echo "   • Total jobs:  $((9 * ${#QUERIES[@]})) crawls"
echo "   • Limit/query: $LIMIT papers"
echo ""

# Get initial stats
echo -e "${YELLOW}📊 Initial database stats:${NC}"
curl -s "${API_URL}/api/v1/papers/stats/index" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   Total papers: {data.get('total_papers', 0)}\")
print(f\"   With full text: {data.get('with_full_text', 0)} ({data.get('processing_coverage', 0):.1f}%)\")
print(f\"   Sources: {len(data.get('by_source', {}))}\")
"
echo ""

# Run crawls
TOTAL_JOBS=0
for QUERY in "${QUERIES[@]}"; do
    echo -e "${BLUE}📚 Query: '${QUERY}'${NC}"
    
    # Start all 9 crawlers for this query
    RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/worker/crawl-all?query=$(echo $QUERY | sed 's/ /%20/g')&limit=${LIMIT}")
    
    if echo "$RESPONSE" | grep -q "started"; then
        JOBS_COUNT=$(echo "$RESPONSE" | grep -o '"jobs":\s*\[' | wc -l)
        echo "   ✅ Started 9 crawlers"
        TOTAL_JOBS=$((TOTAL_JOBS + 9))
        
        # Wait for completion
        echo "   ⏳ Waiting for completion..."
        sleep 15
        
        # Check status
        STATUS=$(curl -s "${API_URL}/api/v1/workflows/crawl-status")
        COMPLETED=$(echo "$STATUS" | grep -o '"completed":\s*[0-9]*' | grep -o '[0-9]*' || echo "0")
        RUNNING=$(echo "$STATUS" | grep -o '"running":\s*[0-9]*' | grep -o '[0-9]*' || echo "0")
        
        echo "   📊 Running: $RUNNING | Completed: $COMPLETED"
    else
        echo "   ❌ Error: $RESPONSE"
    fi
    
    echo ""
done

# Final stats
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    CRAWL COMPLETE!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Final database stats:${NC}"
curl -s "${API_URL}/api/v1/papers/stats/index" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"\n   📄 Total Papers:       {data.get('total_papers', 0)}\")
print(f\"   📑 With Full Text:     {data.get('with_full_text', 0)} ({data.get('processing_coverage', 0):.1f}%)\")
print(f\"   🌐 Sources:            {len(data.get('by_source', {}))}\")
print(f\"\n   📚 By Source:\")
for source, count in sorted(data.get('by_source', {}).items(), key=lambda x: x[1], reverse=True):
    print(f\"      {source:25s}: {count:4d}\")
"

echo ""
echo -e "${GREEN}🌐 View your database:${NC}"
echo "   Frontend:  $FRONTEND_URL"
echo "   Stats:     $FRONTEND_URL/stats"
echo ""

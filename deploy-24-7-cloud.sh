#!/bin/bash
# Deploy ZNAYKA 24/7 Continuous Crawler to Google Cloud
# This runs FOREVER, even when your computer is off

set -e

PROJECT_ID="znayka-fresh-1771794343"
REGION="europe-north1"
API_URL="https://znayka-674193695957.europe-north1.run.app"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ZNAYKA 24/7 CLOUD CRAWLER DEPLOYMENT                       ║${NC}"
echo -e "${BLUE}║     Runs forever in Google Cloud                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if logged in
echo -e "${YELLOW}🔐 Checking GCP login...${NC}"
gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 || {
    echo "Please login first: gcloud auth login"
    exit 1
}

# Set project
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

echo ""
echo -e "${YELLOW}🔨 Building crawler container...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka-crawler:latest -f Dockerfile.crawler .

echo ""
echo -e "${YELLOW}🚀 Creating 24/7 Cloud Run Job...${NC}"

# Delete existing job if exists (to update)
gcloud run jobs delete znayka-crawler-24-7 --quiet 2>/dev/null || true

# Create the continuous crawler job
gcloud run jobs create znayka-crawler-24-7 \
  --image gcr.io/$PROJECT_ID/znayka-crawler:latest \
  --max-retries 10 \
  --task-timeout 24h \
  --memory 4Gi \
  --cpu 4 \
  --set-env-vars="API_URL=$API_URL,CRAWLER_MODE=continuous,MAX_PAPERS_PER_DAY=500000" \
  --wait

echo ""
echo -e "${YELLOW}⏰ Setting up hourly auto-restart...${NC}"

# Delete existing scheduler
gcloud scheduler jobs delete znayka-crawler-scheduler --location=$REGION --quiet 2>/dev/null || true

# Create scheduler that ensures crawler keeps running
gcloud scheduler jobs create http znayka-crawler-scheduler \
  --location=$REGION \
  --schedule="0 * * * *" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/znayka-crawler-24-7:run" \
  --http-method=POST \
  --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com \
  --time-zone="Europe/Moscow"

echo ""
echo -e "${YELLOW}▶️  Starting first crawl...${NC}"
gcloud run jobs execute znayka-crawler-24-7 --wait 2>&1 | tail -20 || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅ 24/7 CRAWLER DEPLOYED!                            ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  🌍 Status:     RUNNING 24/7 IN GOOGLE CLOUD                   ║${NC}"
echo -e "${GREEN}║  ♻️  Restart:    Every hour (auto)                             ║${NC}"
echo -e "${GREEN}║  💪 Power:       4 CPU, 4GB RAM                                ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Your computer can be OFF - crawler keeps running!             ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  MONITORING COMMANDS:                                          ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  View live logs:                                               ║${NC}"
echo -e "${GREEN}║    gcloud logging tail \"resource.labels.job_name=znayka-crawler-24-7\"${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Check database:                                               ║${NC}"
echo -e "${GREEN}║    curl $API_URL/api/v1/papers/stats/index${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Web dashboard:                                                ║${NC}"
echo -e "${GREEN}║    https://znayka-frontend.vercel.app/monitor                  ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  STOP/CONTROL:                                                 ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Pause:    gcloud scheduler jobs pause znayka-crawler-scheduler${NC}"
echo -e "${GREEN}║            --location=$REGION                                  ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Resume:   gcloud scheduler jobs resume znayka-crawler-scheduler${NC}"
echo -e "${GREEN}║            --location=$REGION                                  ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Delete:   gcloud run jobs delete znayka-crawler-24-7 --quiet  ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

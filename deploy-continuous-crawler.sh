#!/bin/bash
# Deploy ZNAYKA Continuous Crawler to GCP
# This creates a 24/7 crawling infrastructure

set -e

PROJECT_ID="znayka-fresh-1771794343"
REGION="europe-north1"
SERVICE_NAME="znayka-crawler"
API_URL="https://znayka-674193695957.europe-north1.run.app"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ZNAYKA 24/7 CONTINUOUS CRAWLER DEPLOYMENT                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Set project
echo -e "${YELLOW}🔧 Setting up GCP project...${NC}"
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Build crawler image
echo ""
echo -e "${YELLOW}🔨 Building crawler image...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka-crawler:latest -f Dockerfile.crawler .

# Create Cloud Run Job for continuous crawling
echo ""
echo -e "${YELLOW}🚀 Creating Cloud Run Job...${NC}"

# Delete existing job if exists
gcloud run jobs delete $SERVICE_NAME --quiet 2>/dev/null || true

# Create new job
gcloud run jobs create $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/znayka-crawler:latest \
  --max-retries 3 \
  --task-timeout 24h \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars="API_URL=$API_URL,PYTHONUNBUFFERED=1" \
  --wait

echo ""
echo -e "${GREEN}✅ Crawler job created!${NC}"

# Create scheduled execution (every hour)
echo ""
echo -e "${YELLOW}⏰ Creating scheduler...${NC}"

# Delete existing scheduler
 gcloud scheduler jobs delete znayka-crawler-scheduler --location=$REGION --quiet 2>/dev/null || true

# Create new scheduler
gcloud scheduler jobs create http znayka-crawler-scheduler \
  --location=$REGION \
  --schedule="0 * * * *" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$SERVICE_NAME:run" \
  --http-method=POST \
  --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com \
  --time-zone="Europe/Moscow"

echo ""
echo -e "${GREEN}✅ Scheduler created! Runs every hour${NC}"

# Execute first run immediately
echo ""
echo -e "${YELLOW}▶️  Starting first crawl...${NC}"
gcloud run jobs execute $SERVICE_NAME --wait 2>&1 | tail -20 || true

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           🎉 CONTINUOUS CRAWLER DEPLOYED!                      ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Status:     Running 24/7                                      ║${NC}"
echo -e "${GREEN}║  Schedule:   Every hour (via Cloud Scheduler)                  ║${NC}"
echo -e "${GREEN}║  Job Name:   $SERVICE_NAME${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Commands:                                                     ║${NC}"
echo -e "${GREEN}║    View logs:   gcloud logging tail \"resource.type=cloud_run_job\"  ║${NC}"
echo -e "${GREEN}║    Execute:    gcloud run jobs execute $SERVICE_NAME${NC}"
echo -e "${GREEN}║    Stop:       gcloud scheduler jobs pause znayka-crawler-scheduler${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Monitor:     https://znayka-frontend.vercel.app/stats        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

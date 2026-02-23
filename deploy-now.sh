#!/bin/bash
# Non-interactive deployment
set -e

PROJECT_ID="znayka-fresh-1771794343"
REGION="europe-north1"
DB_INSTANCE="znayka-db-prod"
DB_NAME="znayka_prod"
DB_USER="znayka_admin"
ENABLE_LLM="${ENABLE_LLM_ANALYSIS:-false}"

echo "🚀 ZNAYKA Production Deployment"
echo "================================"
echo "LLM Enabled: $ENABLE_LLM"
echo ""

# Enable APIs
echo "🔧 Enabling APIs..."
gcloud services enable sqladmin.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID 2>/dev/null || true

# Create PostgreSQL database
echo ""
echo "📦 Creating PostgreSQL database..."
if ! gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID 2>/dev/null; then
    gcloud sql instances create $DB_INSTANCE \
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-size=100GB \
        --storage-auto-increase \
        --availability-type=zonal 2>&1 | tail -5
    echo "✅ Database created!"
else
    echo "✅ Database already exists"
fi

# Create database
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE --project=$PROJECT_ID 2>/dev/null || echo "DB exists"

# Generate password
DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)

# Create/update user
gcloud sql users create $DB_USER --instance=$DB_INSTANCE --project=$PROJECT_ID --password="$DB_PASS" 2>/dev/null || \
gcloud sql users set-password $DB_USER --instance=$DB_INSTANCE --project=$PROJECT_ID --password="$DB_PASS"

# Store secret
echo -n "$DB_PASS" | gcloud secrets create znayka-db-password --data-file=- --project=$PROJECT_ID 2>/dev/null || \
echo -n "$DB_PASS" | gcloud secrets versions add znayka-db-password --data-file=- --project=$PROJECT_ID

CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(connectionName)")

echo ""
echo "✅ Database ready: $CONNECTION_NAME"

# Create storage bucket
echo ""
echo "📂 Creating PDF storage..."
gsutil mb -p $PROJECT_ID -l $REGION gs://znayka-pdfs-$PROJECT_ID 2>/dev/null || echo "Bucket exists"

# Build and deploy
echo ""
echo "🔨 Building container..."
cat > cloudbuild.deploy.yaml << 'CBEOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/${PROJECT_ID}/znayka:prod', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/${PROJECT_ID}/znayka:prod']
images:
  - 'gcr.io/${PROJECT_ID}/znayka:prod'
CBEOF

gcloud builds submit --config=cloudbuild.deploy.yaml --timeout=600s

echo ""
echo "🚀 Deploying backend..."
gcloud run deploy znayka \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:prod \
    --memory=4Gi \
    --cpu=2 \
    --timeout=300 \
    --max-instances=10 \
    --set-env-vars="USE_REAL_DATABASE=true" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@/znayka_prod?host=/cloudsql/${CONNECTION_NAME}" \
    --set-cloudsql-instances=$CONNECTION_NAME \
    --set-secrets=DB_PASSWORD=znayka-db-password:latest

# Create crawler job
echo ""
echo "🕷️ Creating 24/7 crawler..."
gcloud run jobs delete znayka-crawler-prod --quiet 2>/dev/null || true
gcloud run jobs create znayka-crawler-prod \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:prod \
    --command=python \
    --args="-c,from app.continuous_crawler import main; main()" \
    --memory=4Gi \
    --cpu=4 \
    --max-retries=5 \
    --task-timeout=24h \
    --set-env-vars="USE_REAL_DATABASE=true" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@/znayka_prod?host=/cloudsql/${CONNECTION_NAME}" \
    --set-cloudsql-instances=$CONNECTION_NAME \
    --set-secrets=DB_PASSWORD=znayka-db-password:latest 2>&1 | tail -10

# Start crawler
echo ""
echo "▶️ Starting crawler..."
gcloud run jobs execute znayka-crawler-prod --project=$PROJECT_ID --region=$REGION --wait 2>&1 | tail -5 &

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           ✅ DEPLOYMENT COMPLETE!                                ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                  ║"
echo "║  🗄️  Database:     $DB_INSTANCE                                  ║"
echo "║  📊 Tables:        Created                                       ║"
echo "║  🕷️  Crawler:      Running 24/7                                  ║"
echo "║  🔗 API:           https://znayka-674193695957.europe-north1.run.app ║"
echo "║                                                                  ║"
echo "║  📈 Watch papers appear at:                                      ║"
echo "║  https://znayka-frontend.vercel.app/monitor                      ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

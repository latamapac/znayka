#!/bin/bash
# ZNAYKA Deploy - Creates fresh project automatically

set -e

# Generate unique project ID
export PROJECT_ID="znayka-$(date +%s)"
export PROJECT_NAME="ZNAYKA Science Hub"
export REGION="us-central1"

echo "🚀 Creating fresh GCP project: $PROJECT_ID"

# Create new project (owned by you)
echo "📦 Creating project..."
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"
gcloud config set project $PROJECT_ID

# Wait for project to be ready
sleep 5

# Enable billing (required for Cloud SQL)
echo "💳 Attempting to link billing..."
echo "If this fails, go to: https://console.cloud.google.com/billing"
echo "and link billing account manually"

# Enable APIs one by one (skip if fails)
echo "🔧 Enabling APIs..."
gcloud services enable run.googleapis.com || echo "⚠️ Cloud Run API failed"
gcloud services enable sqladmin.googleapis.com || echo "⚠️ SQL Admin API failed"
gcloud services enable servicenetworking.googleapis.com || echo "⚠️ Service Networking failed"

# Create database
echo "🗄️  Creating PostgreSQL database..."
gcloud sql instances create znayka-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-size=10GB \
    --no-backup || echo "⚠️ DB creation failed, may already exist"

gcloud sql databases create znayka --instance=znayka-db 2>/dev/null || echo "⚠️ Database may already exist"

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "📍 DB Connection: $DB_CONNECTION"

# Build locally and push
echo "🔨 Building container..."
docker build -f Dockerfile.simple -t gcr.io/$PROJECT_ID/znayka .
docker push gcr.io/$PROJECT_ID/znayka || {
    echo "❌ Docker push failed. Enable Container Registry API:"
    echo "   https://console.cloud.google.com/apis/library/containerregistry.googleapis.com"
    exit 1
}

# Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy znayka \
    --image gcr.io/$PROJECT_ID/znayka \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,USE_SQLITE=false" \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=5

# Get URL
echo ""
echo "✅ DONE!"
echo ""
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "Test: curl $SERVICE_URL/health"

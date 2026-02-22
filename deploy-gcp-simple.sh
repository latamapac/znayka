#!/bin/bash
# ZNAYKA Deploy Script - Simple version (no Vertex AI)

set -e

export PROJECT_ID=znayka-science
export REGION=us-central1

echo "🚀 Deploying ZNAYKA to Google Cloud (Simple Mode)"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable basic APIs only (no aiplatform)
echo "🔧 Enabling APIs..."
gcloud services enable run sqladmin cloudbuild

# Create database
echo "🗄️  Checking database..."
if gcloud sql instances describe znayka-db --quiet 2>/dev/null; then
    echo "✅ Database already exists"
else
    echo "📦 Creating PostgreSQL database..."
    gcloud sql instances create znayka-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-size=10GB
    
    gcloud sql databases create znayka --instance=znayka-db
fi

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "📍 DB Connection: $DB_CONNECTION"

# Service account
echo "🔐 Checking service account..."
if gcloud iam service-accounts describe znayka-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet 2>/dev/null; then
    echo "✅ Service account exists"
else
    echo "👤 Creating service account..."
    gcloud iam service-accounts create znayka-sa \
        --display-name="ZNAYKA Service Account"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/cloudsql.client"
fi

# Build with simple Dockerfile (no Vertex AI)
echo "🔨 Building container..."
docker build -f Dockerfile.simple -t gcr.io/$PROJECT_ID/znayka .
docker push gcr.io/$PROJECT_ID/znayka

# Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy znayka \
    --image gcr.io/$PROJECT_ID/znayka \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=znayka-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=$DB_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,USE_SQLITE=false" \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=5

# Get URL
echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "Test: curl $SERVICE_URL/health"
echo "Docs: $SERVICE_URL/docs"

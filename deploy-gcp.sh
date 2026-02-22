#!/bin/bash
# ZNAYKA Deploy Script for Google Cloud
# Project: project-81f8f179-6791-4514-918

set -e

export PROJECT_ID=project-81f8f179-6791-4514-918
export REGION=us-central1

echo "🚀 Deploying ZNAYKA to Google Cloud"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# 1. Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# 2. Enable APIs
echo "🔧 Enabling APIs..."
gcloud services enable run sqladmin aiplatform storage cloudbuild

# 3. Check if database exists
echo "🗄️  Checking database..."
if gcloud sql instances describe znayka-db --quiet 2>/dev/null; then
    echo "✅ Database already exists"
else
    echo "📦 Creating PostgreSQL database..."
    gcloud sql instances create znayka-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-size=10GB \
        --availability-type=zonal
    
    echo "📝 Creating database..."
    gcloud sql databases create znayka --instance=znayka-db
fi

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "📍 DB Connection: $DB_CONNECTION"

# 4. Check/create service account
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
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/aiplatform.user"
fi

# 5. Build
echo "🔨 Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka

# 6. Deploy
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy znayka \
    --image gcr.io/$PROJECT_ID/znayka \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=znayka-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=$DB_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,USE_SQLITE=false" \
    --memory=2Gi \
    --cpu=2 \
    --max-instances=10

# 7. Get URL
echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "Test it:"
echo "  curl $SERVICE_URL/health"
echo ""
echo "API Docs: $SERVICE_URL/docs"

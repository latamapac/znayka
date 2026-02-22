#!/bin/bash
# ZNAYKA - Continue deploy with EXISTING project

set -e

export PROJECT_ID="znayka-fresh-1771794343"
export REGION="us-central1"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🚀 ZNAYKA CONTINUE DEPLOY                        ║"
echo "║           (Using existing project)                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Project: $PROJECT_ID"
echo ""

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID
echo ""

# Check/Wait for Cloud SQL
echo "🗄️  Checking Cloud SQL status..."
MAX_RETRIES=30
RETRY_COUNT=0

while true; do
    STATUS=$(gcloud sql instances describe znayka-db --format='value(state)' 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$STATUS" = "RUNNABLE" ]; then
        echo "✅ Database is ready!"
        break
    elif [ "$STATUS" = "PENDING_CREATE" ]; then
        echo "⏳  Database still creating... waiting 10s (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
        sleep 10
        RETRY_COUNT=$((RETRY_COUNT+1))
        
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "⚠️  Timeout waiting for database. Check status:"
            echo "   gcloud sql instances describe znayka-db"
            exit 1
        fi
    elif [ "$STATUS" = "NOT_FOUND" ]; then
        echo "❌ Database not found. Creating now..."
        gcloud sql instances create znayka-db \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=$REGION \
            --storage-size=10GB || {
                echo "⚠️  Failed to create database. Create manually:"
                echo "   https://console.cloud.google.com/sql/instances/create"
                exit 1
            }
        gcloud sql databases create znayka --instance=znayka-db 2>/dev/null || true
    else
        echo "⚠️  Database status: $STATUS"
        echo "   Check: gcloud sql instances describe znayka-db"
        sleep 10
    fi
done

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "📍 DB Connection: $DB_CONNECTION"
echo ""

# Create service account (if not exists)
echo "👤 Checking service account..."
if gcloud iam service-accounts describe znayka-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet 2>/dev/null; then
    echo "✅ Service account exists"
else
    echo "Creating service account..."
    gcloud iam service-accounts create znayka-sa \
        --display-name="ZNAYKA Service Account"
fi

# Add permissions
echo "🔐 Adding permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client" --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.editor" --quiet 2>/dev/null || true

echo ""

# Configure Docker
echo "🐳 Configuring Docker..."
gcloud auth configure-docker --quiet
echo ""

# Build container
echo "🔨 Building container..."
docker build -f Dockerfile.simple -t gcr.io/$PROJECT_ID/znayka .
docker push gcr.io/$PROJECT_ID/znayka
echo "✅ Container built and pushed"
echo ""

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy znayka \
    --image gcr.io/$PROJECT_ID/znayka \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=znayka-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=$DB_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,USE_SQLITE=false,PROJECT_ID=$PROJECT_ID" \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=5 \
    --timeout=300 \
    --concurrency=80

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🌐 URL: $SERVICE_URL"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Test: curl $SERVICE_URL/health"
echo "Docs: $SERVICE_URL/docs"
echo ""

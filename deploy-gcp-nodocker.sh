#!/bin/bash
# ZNAYKA - Deploy WITHOUT Docker (uses Cloud Build)

set -e

export PROJECT_ID="znayka-fresh-1771794343"
export REGION="us-central1"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🚀 ZNAYKA DEPLOY (No Docker Required)            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Project: $PROJECT_ID"
echo ""

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID
echo ""

# Enable Cloud Build API
echo "🔧 Enabling Cloud Build API..."
gcloud services enable cloudbuild.googleapis.com --quiet
echo "✅ Cloud Build enabled"
echo ""

# Wait for Cloud SQL
echo "🗄️  Checking Cloud SQL..."
MAX_RETRIES=30
RETRY_COUNT=0

while true; do
    STATUS=$(gcloud sql instances describe znayka-db --format='value(state)' 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$STATUS" = "RUNNABLE" ]; then
        echo "✅ Database ready!"
        break
    elif [ "$STATUS" = "PENDING_CREATE" ]; then
        echo "⏳  Database creating... waiting (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
        sleep 10
        RETRY_COUNT=$((RETRY_COUNT+1))
        
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "⚠️  Timeout. Check status:"
            echo "   gcloud sql instances describe znayka-db"
            exit 1
        fi
    else
        echo "Status: $STATUS, waiting..."
        sleep 10
    fi
done

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "📍 DB Connection: $DB_CONNECTION"
echo ""

# Service account
echo "👤 Service account..."
if ! gcloud iam service-accounts describe znayka-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet 2>/dev/null; then
    gcloud iam service-accounts create znayka-sa --display-name="ZNAYKA"
fi

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client" --quiet 2>/dev/null || true

echo ""

# BUILD WITH CLOUD BUILD (no local Docker needed)
echo "🔨 Building with Cloud Build..."
gcloud builds submit --config=cloudbuild.yaml --timeout=20m
echo "✅ Build complete"
echo ""

# DEPLOY
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy znayka \
    --image gcr.io/$PROJECT_ID/znayka:latest \
    --platform managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=znayka-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --add-cloudsql-instances=$DB_CONNECTION \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,USE_SQLITE=false,PROJECT_ID=$PROJECT_ID" \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=5 \
    --timeout=300

echo ""
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYED: $SERVICE_URL"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Test: curl $SERVICE_URL/health"
echo ""

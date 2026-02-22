#!/bin/bash
# ZNAYKA - Fresh Deploy (delete old, create new)

set -e

export PROJECT_ID="znayka-fresh-$(date +%s)"
export PROJECT_NAME="ZNAYKA Science Hub"
export REGION="us-central1"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🚀 ZNAYKA FRESH DEPLOY                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Create new project
echo "📦 Step 1: Creating new project..."
gcloud projects create $PROJECT_ID --name="$PROJECT_NAME" --set-as-default
echo "✅ Project created: $PROJECT_ID"
echo ""

# Step 2: Link billing (you need to have a billing account with credits)
echo "💳 Step 2: Linking billing account..."
echo "Available billing accounts:"
gcloud billing accounts list --format="table(displayName,name,open)"
echo ""

# Try to auto-link billing
BILLING_ACCOUNT=$(gcloud billing accounts list --format="value(name)" --limit=1)
if [ -n "$BILLING_ACCOUNT" ]; then
    echo "Linking billing account: $BILLING_ACCOUNT"
    gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT || {
        echo "⚠️  Auto-link failed. Please link manually:"
        echo "   https://console.cloud.google.com/billing/projects"
        echo ""
        read -p "Press ENTER after linking billing..."
    }
else
    echo "⚠️  No billing account found. Please create one:"
    echo "   https://console.cloud.google.com/billing"
    exit 1
fi

echo "✅ Billing linked"
echo ""

# Step 3: Enable APIs
echo "🔧 Step 3: Enabling APIs..."
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable containerregistry.googleapis.com
echo "✅ APIs enabled"
echo ""

# Step 4: Create Cloud SQL (PostgreSQL)
echo "🗄️  Step 4: Creating PostgreSQL database..."
gcloud sql instances create znayka-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-size=10GB \
    --availability-type=zonal \
    --no-backup

gcloud sql databases create znayka --instance=znayka-db

export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')
echo "✅ Database created: $DB_CONNECTION"
echo ""

# Step 5: Create service account
echo "👤 Step 5: Creating service account..."
gcloud iam service-accounts create znayka-sa \
    --display-name="ZNAYKA Service Account"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.editor"

echo "✅ Service account created"
echo ""

# Step 6: Configure Docker
echo "🐳 Step 6: Configuring Docker..."
gcloud auth configure-docker
echo "✅ Docker configured"
echo ""

# Step 7: Build container
echo "🔨 Step 7: Building container..."
cd /Users/mark/russian-science-hub
docker build -f Dockerfile.simple -t gcr.io/$PROJECT_ID/znayka .
docker push gcr.io/$PROJECT_ID/znayka
echo "✅ Container built and pushed"
echo ""

# Step 8: Deploy to Cloud Run
echo "🚀 Step 8: Deploying to Cloud Run..."
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

echo "✅ Deployed to Cloud Run"
echo ""

# Step 9: Get URL
echo "📍 Step 9: Getting service URL..."
export SERVICE_URL=$(gcloud run services describe znayka --region=$REGION --format='value(status.url)')

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           ✅ ZNAYKA DEPLOYED SUCCESSFULLY!                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "📋 Test commands:"
echo "   curl $SERVICE_URL/health"
echo "   curl $SERVICE_URL/"
echo ""
echo "📖 API Docs: $SERVICE_URL/docs"
echo ""
echo "🔍 Project ID: $PROJECT_ID"
echo "   Save this for future reference!"
echo ""

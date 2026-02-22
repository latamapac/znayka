# ZNAYKA on Google Cloud Platform

## Prerequisites

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Quick Deploy (5 minutes)

```bash
# 1. Enable APIs
gcloud services enable run sqladmin aiplatform storage cloudbuild

# 2. Set project
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1

# 3. Create Cloud SQL (PostgreSQL with pgvector)
gcloud sql instances create znayka-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-size=10GB \
  --availability-type=zonal

# Get connection name
export DB_CONNECTION=$(gcloud sql instances describe znayka-db --format='value(connectionName)')

# Create database
gcloud sql databases create znayka --instance=znayka-db

# 4. Create service account for Cloud Run
gcloud iam service-accounts create znayka-sa \
  --display-name="ZNAYKA Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:znayka-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# 5. Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka

gcloud run deploy znayka \
  --image gcr.io/$PROJECT_ID/znayka \
  --platform managed \
  --region=$REGION \
  --allow-unauthenticated \
  --service-account=znayka-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://znayka:znayka@/znayka?host=/cloudsql/$DB_CONNECTION,USE_SQLITE=false,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --add-cloudsql-instances=$DB_CONNECTION

# 6. Get URL
gcloud run services describe znayka --region=$REGION --format='value(status.url)'
```

## Architecture

- **Cloud Run**: Serverless FastAPI (scales to zero)
- **Cloud SQL**: PostgreSQL 15 + pgvector (managed)
- **Vertex AI**: Embeddings API (no local ML)
- **Cloud Storage**: PDF storage (optional)

## Cost

- **Free tier**: $0 (within limits)
- **Paid**: ~$12/month (10K papers indexed)

## Features

✅ Auto-scaling (0 → N)  
✅ Managed PostgreSQL with pgvector  
✅ Vertex AI for embeddings (no PyTorch)  
✅ $300 free credits  
✅ Always free tier available

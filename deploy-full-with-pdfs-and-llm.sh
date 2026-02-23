#!/bin/bash
# ZNAYKA Full Deployment: PostgreSQL + PDFs + LLM Analysis
# Costs: ~$150-300/month for 100K papers with full PDFs + LLM

set -e

PROJECT_ID="znayka-fresh-1771794343"
REGION="europe-north1"
DB_INSTANCE="znayka-db-full"
DB_NAME="znayka_full"
DB_USER="znayka_admin"
R2_BUCKET="znayka-pdfs"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ZNAYKA FULL DEPLOYMENT: DB + PDFs + LLM                         ║"
echo "║  Costs: ~$150-300/month for 100K papers                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if user understands costs
echo "⚠️  This will create infrastructure with ongoing costs:"
echo "   • PostgreSQL (db-n1-standard-2): ~$50/month"
echo "   • PDF Storage (500GB): ~$7.50/month"
echo "   • PDF Bandwidth: ~$20-50/month"
echo "   • LLM API (OpenAI): ~$50-200/month depending on usage"
echo "   • Cloud Run (backend): ~$30/month"
echo ""
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

# Enable APIs
echo "🔧 Enabling APIs..."
gcloud services enable sqladmin.googleapis.com --project=$PROJECT_ID
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create PostgreSQL database (larger instance for PDF processing)
echo ""
echo "📦 Creating PostgreSQL database (db-n1-standard-2)..."
if ! gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID 2>/dev/null; then
    gcloud sql instances create $DB_INSTANCE \
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-n1-standard-2 \
        --region=$REGION \
        --storage-size=500GB \
        --storage-auto-increase \
        --availability-type=regional \
        --backup-start-time="03:00"
    
    echo "✅ Database instance created!"
else
    echo "✅ Database instance already exists"
fi

# Create database
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE --project=$PROJECT_ID 2>/dev/null || echo "Database already exists"

# Generate passwords
DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-24)
OPENAI_KEY=$(read -p "Enter OpenAI API Key (for LLM analysis, or press Enter to skip): " key && echo $key)

# Create database user
gcloud sql users create $DB_USER \
    --instance=$DB_INSTANCE \
    --project=$PROJECT_ID \
    --password="$DB_PASS" 2>/dev/null || {
    echo "User exists, updating password..."
    gcloud sql users set-password $DB_USER \
        --instance=$DB_INSTANCE \
        --project=$PROJECT_ID \
        --password="$DB_PASS"
}

# Store secrets
echo ""
echo "🔐 Storing secrets..."
echo -n "$DB_PASS" | gcloud secrets create znayka-db-password --data-file=- --project=$PROJECT_ID 2>/dev/null || \
    echo -n "$DB_PASS" | gcloud secrets versions add znayka-db-password --data-file=- --project=$PROJECT_ID

if [ -n "$OPENAI_KEY" ]; then
    echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- --project=$PROJECT_ID 2>/dev/null || \
        echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key --data-file=- --project=$PROJECT_ID
fi

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(connectionName)")

echo ""
echo "🔗 Connection Name: $CONNECTION_NAME"

# Create storage bucket for PDFs (using Google Cloud Storage)
echo ""
echo "📂 Creating PDF storage bucket..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$R2_BUCKET 2>/dev/null || echo "Bucket already exists"

# Create backend environment config
cat > backend/.env.production << EOF
# Full Production Config with PDFs + LLM
USE_REAL_DATABASE=true
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@/znayka_full?host=/cloudsql/$CONNECTION_NAME
CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME
DB_PASSWORD=$DB_PASS

# PDF Storage
PDF_STORAGE_TYPE=gcs
PDF_STORAGE_BUCKET=$R2_BUCKET
PDF_STORAGE_PATH=/app/storage/pdfs

# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
ENABLE_LLM_ANALYSIS=true
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.3

# Crawler Config
CRAWLER_MODE=continuous
MAX_PAPERS_PER_DAY=100000
PAPERS_PER_QUERY=1000
DOWNLOAD_PDFS=true
ENABLE_FULLTEXT_INDEXING=true

# API
API_URL=https://znayka-674193695957.europe-north1.run.app
EOF

echo "✅ Created production environment config"

# Update Cloud Build config to include all dependencies
cat > cloudbuild.full.yaml << 'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/znayka:full', '-f', 'Dockerfile.full', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/znayka:full']
images:
  - 'gcr.io/$PROJECT_ID/znayka:full'
EOF

# Create full Dockerfile with all dependencies
cat > Dockerfile.full << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including pdf processing
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-rus \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages for PDF + LLM
RUN pip install --no-cache-dir \
    langchain \
    langchain-openai \
    pypdf \
    pdf2image \
    pytesseract \
    google-cloud-storage \
    tiktoken

# Copy application
COPY backend/ ./backend/
COPY crawlers/ ./crawlers/

# Create directories
RUN mkdir -p /app/storage/pdfs /app/logs

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting ZNAYKA Full Stack..."\n\
echo "Mode: Database + PDFs + LLM"\n\
echo "DB: $USE_REAL_DATABASE"\n\
echo "PDF: $DOWNLOAD_PDFS"\n\
echo "LLM: $ENABLE_LLM_ANALYSIS"\n\
cd /app\n\
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
EOF

echo ""
echo "🔨 Building full-stack container (this takes 5-10 minutes)..."
gcloud builds submit --config=cloudbuild.full.yaml

# Deploy backend with full capabilities
echo ""
echo "🚀 Deploying backend with DB + PDFs + LLM..."
gcloud run deploy znayka \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:full \
    --memory=8Gi \
    --cpu=4 \
    --timeout=600 \
    --max-instances=10 \
    --set-env-vars="USE_REAL_DATABASE=true" \
    --set-env-vars="DOWNLOAD_PDFS=true" \
    --set-env-vars="ENABLE_LLM_ANALYSIS=true" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@/znayka_full?host=/cloudsql/${CONNECTION_NAME}" \
    --set-env-vars="PDF_STORAGE_BUCKET=${R2_BUCKET}" \
    --set-cloudsql-instances=$CONNECTION_NAME \
    --set-secrets=DB_PASSWORD=znayka-db-password:latest,OPENAI_API_KEY=openai-api-key:latest

# Create PDF downloader worker
echo ""
echo "📥 Creating PDF downloader worker..."
cat > pdf-worker.yaml << WORKEREOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: znayka-pdf-worker
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    spec:
      containers:
      - image: gcr.io/$PROJECT_ID/znayka:full
        command: ["python", "-c", "from backend.app.pdf_manager import start_pdf_worker; import asyncio; asyncio.run(start_pdf_worker())"]
        resources:
          limits:
            memory: 4Gi
            cpu: 2
      timeoutSeconds: 3600
WORKEREOF

# Deploy PDF worker
gcloud run jobs replace pdf-worker.yaml --project=$PROJECT_ID --region=$REGION 2>/dev/null || \
    gcloud run jobs create znayka-pdf-worker \
        --project=$PROJECT_ID \
        --region=$REGION \
        --image gcr.io/$PROJECT_ID/znayka:full \
        --command=python \
        --args="-c,from backend.app.pdf_manager import start_pdf_worker; import asyncio; asyncio.run(start_pdf_worker())" \
        --memory=4Gi \
        --cpu=2 \
        --max-retries=3

# Create LLM analysis worker
echo ""
echo "🤖 Creating LLM analysis worker..."
gcloud run jobs create znayka-llm-worker \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:full \
    --command=python \
    --args="-c,from backend.app.llm_analyzer import start_llm_worker; import asyncio; asyncio.run(start_llm_worker())" \
    --memory=4Gi \
    --cpu=2 \
    --max-retries=3 \
    --set-secrets=OPENAI_API_KEY=openai-api-key:latest 2>/dev/null || echo "LLM worker already exists"

# Deploy 24/7 crawler
echo ""
echo "🕷️ Deploying 24/7 crawler..."
gcloud run jobs create znayka-crawler-full \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:full \
    --command=python \
    --args="-m,backend.app.continuous_crawler,--limit,1000,--mode,continuous" \
    --memory=4Gi \
    --cpu=4 \
    --max-retries=10 \
    --task-timeout=24h

# Create schedulers
echo ""
echo "⏰ Creating schedulers..."

# Crawler scheduler
gcloud scheduler jobs create http znayka-crawler-scheduler \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="0 */2 * * *" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/znayka-crawler-full:run" \
    --http-method=POST \
    --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com 2>/dev/null || true

# PDF worker scheduler (runs every 10 minutes)
gcloud scheduler jobs create http znayka-pdf-scheduler \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="*/10 * * * *" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/znayka-pdf-worker:run" \
    --http-method=POST \
    --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com 2>/dev/null || true

# LLM analysis scheduler (runs every 30 minutes)
gcloud scheduler jobs create http znayka-llm-scheduler \
    --project=$PROJECT_ID \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/znayka-llm-worker:run" \
    --http-method=POST \
    --oauth-service-account-email=$PROJECT_ID@appspot.gserviceaccount.com 2>/dev/null || true

# Start everything
echo ""
echo "🚀 Starting all workers..."
gcloud run jobs execute znayka-crawler-full --project=$PROJECT_ID --region=$REGION --wait &
gcloud run jobs execute znayka-pdf-worker --project=$PROJECT_ID --region=$REGION --wait &

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           ✅ FULL DEPLOYMENT COMPLETE!                           ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                  ║"
echo "║  🗄️  Database:     PostgreSQL (db-n1-standard-2)                ║"
echo "║  💾 PDF Storage:   Google Cloud Storage ($R2_BUCKET)            ║"
echo "║  🤖 LLM:          OpenAI GPT-4o-mini                            ║"
echo "║  🕷️  Crawler:      Running 24/7                                 ║"
echo "║  📥 PDF Worker:   Downloading PDFs every 10 min                ║"
echo "║  🧠 LLM Worker:   Analyzing papers every 30 min                ║"
echo "║                                                                  ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  MONTHLY COSTS:                                                  ║"
echo "║    Database:      ~$50/month                                     ║"
echo "║    PDF Storage:   ~$7.50/month (for 500GB)                       ║"
echo "║    Bandwidth:     ~$20-50/month                                  ║"
echo "║    LLM API:       ~$50-200/month (usage-based)                   ║"
echo "║    Cloud Run:     ~$50/month                                     ║"
echo "║    ─────────────────────────                                     ║"
echo "║    TOTAL:         ~$180-360/month                                ║"
echo "║                                                                  ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  URLs:                                                           ║"
echo "║    Frontend:  https://znayka-frontend.vercel.app                 ║"
echo "║    Monitor:   https://znayka-frontend.vercel.app/monitor         ║"
echo "║    API:       https://znayka-674193695957.europe-north1.run.app  ║"
echo "║                                                                  ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  COMMANDS:                                                       ║"
echo "║    View logs:  gcloud logging tail \"resource.type=cloud_run_job\" ║"
echo "║    Stop all:   ./stop-all-workers.sh                             ║"
echo "║    Check DB:   gcloud sql connect $DB_INSTANCE --database=$DB_NAME║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Save credentials
cat > deployment-credentials.txt << CREDS
ZNAYKA FULL DEPLOYMENT CREDENTIALS
==================================
Database: $DB_INSTANCE
Database Name: $DB_NAME
Username: $DB_USER
Password: $DB_PASS
Connection: $CONNECTION_NAME
PDF Bucket: $R2_BUCKET

Save this file securely!
CREDS

echo "💾 Credentials saved to: deployment-credentials.txt"

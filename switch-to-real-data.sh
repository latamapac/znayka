#!/bin/bash
# Switch ZNAYKA from mock data to REAL PostgreSQL database
# This enables real crawlers and actual paper storage

set -e

PROJECT_ID="znayka-fresh-1771794343"
REGION="europe-north1"
DB_INSTANCE="znayka-db"
DB_NAME="znayka_db"
DB_USER="znayka_user"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     SWITCHING FROM MOCK TO REAL DATA                             ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if database already exists
echo "🔍 Checking for existing database..."
if gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID 2>/dev/null; then
    echo "✅ Database instance already exists: $DB_INSTANCE"
    DB_EXISTS=true
else
    echo "⚠️  Database instance not found. Creating new one..."
    DB_EXISTS=false
fi

if [ "$DB_EXISTS" = false ]; then
    echo ""
    echo "📦 Creating PostgreSQL database (this takes 5-10 minutes)..."
    gcloud sql instances create $DB_INSTANCE \
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-size=100GB \
        --storage-auto-increase \
        --availability-type=zonal \
        --no-backup
    
    echo "✅ Database instance created!"
    
    # Create database
    echo "📂 Creating database '$DB_NAME'..."
    gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE --project=$PROJECT_ID
    
    # Generate random password
    DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)
    
    # Create user
    echo "👤 Creating database user..."
    gcloud sql users create $DB_USER \
        --instance=$DB_INSTANCE \
        --project=$PROJECT_ID \
        --password="$DB_PASS"
    
    echo ""
    echo "📝 Database Credentials (SAVE THESE!):"
    echo "   Instance: $DB_INSTANCE"
    echo "   Database: $DB_NAME"
    echo "   User:     $DB_USER"
    echo "   Password: $DB_PASS"
    echo ""
else
    # Get existing credentials
    echo ""
    echo "🔐 Please enter existing database password:"
    read -s DB_PASS
    echo ""
fi

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format="value(connectionName)")

echo ""
echo "🔗 Connection Name: $CONNECTION_NAME"

# Create .env file for local development
cat > backend/.env << EOF
# Database Configuration
USE_REAL_DATABASE=true
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@/znayka_db?host=/cloudsql/$CONNECTION_NAME
CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME

# API Configuration
API_URL=https://znayka-674193695957.europe-north1.run.app
EOF

echo "✅ Created backend/.env with database credentials"

# Update Cloud Run service to use real database
echo ""
echo "🚀 Updating Cloud Run service to use real database..."
gcloud run services update znayka \
    --project=$PROJECT_ID \
    --region=$REGION \
    --set-env-vars="USE_REAL_DATABASE=true" \
    --set-env-vars="DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@/znayka_db?host=/cloudsql/$CONNECTION_NAME" \
    --set-cloudsql-instances=$CONNECTION_NAME

echo "✅ Cloud Run service updated!"

# Deploy the updated backend
echo ""
echo "🔨 Rebuilding backend with real database support..."
gcloud builds submit --config=cloudbuild.full.yaml

gcloud run deploy znayka \
    --project=$PROJECT_ID \
    --region=$REGION \
    --image gcr.io/$PROJECT_ID/znayka:full \
    --memory=4Gi \
    --cpu=4 \
    --timeout=300

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     ✅ SWITCHED TO REAL DATA!                                    ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                  ║"
echo "║  Now you need to:                                                ║"
echo "║                                                                  ║"
echo "║  1. Initialize database tables:                                  ║"
echo "║     gcloud run services update znayka \"                         ║"
echo "║       --project=$PROJECT_ID \"                                  ║"
echo "║       --region=$REGION \"                                        ║"
echo "║       --command="python,-c,from app.database_real import init_db; import asyncio; asyncio.run(init_db())\""
echo "║                                                                  ║"
echo "║  2. Start real crawlers:                                         ║"
echo "║     ./deploy-24-7-cloud.sh                                       ║"
echo "║                                                                  ║"
echo "║  3. Watch real papers appear:                                    ║"
echo "║     https://znayka-frontend.vercel.app/monitor                   ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

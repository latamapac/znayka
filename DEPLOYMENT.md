# Deployment Guide - Russian Science Hub

## Overview

This guide covers deploying the Russian Science Hub to Railway and setting up Temporal.io for crawler orchestration.

## Railway Deployment

### Prerequisites

- Railway CLI installed (`npm install -g @railway/cli`)
- Railway account
- Git repository with your code

### Steps

1. **Login to Railway:**
   ```bash
   railway login
   ```

2. **Initialize project:**
   ```bash
   railway init
   ```

3. **Add PostgreSQL database:**
   ```bash
   railway add --database postgres
   ```
   This automatically sets `DATABASE_URL` environment variable.

4. **Add Redis (optional, for caching):**
   ```bash
   railway add --database redis
   ```

5. **Deploy the backend:**
   ```bash
   cd backend
   railway up
   ```

6. **Add environment variables:**
   ```bash
   railway variables set USE_SQLITE=false
   railway variables set USE_TEMPORAL=false  # Set to true when Temporal is ready
   railway variables set SEED_DATABASE=true  # First deployment only
   ```

7. **Verify deployment:**
   Check the deployment URL with:
   ```bash
   railway status
   ```
   Visit `/health` and `/docs` endpoints.

## Why Railway?

The main issue with local development is macOS SSL certificate verification blocking crawlers. Railway provides:

- **Linux environment** - No SSL certificate issues
- **PostgreSQL + pgvector** - Built-in vector search support
- **Automatic HTTPS** - Secure by default
- **Auto-scaling** - Handles traffic spikes

## Temporal.io Integration

### Local Development

Use Docker Compose for local Temporal:

```bash
# Start all services
docker-compose up -d

# Access services:
# - API: http://localhost:8080
# - Frontend: http://localhost:3000
# - Temporal UI: http://localhost:8233
# - PostgreSQL: localhost:5432
```

### Temporal Workflows

The system includes several workflows:

1. **CrawlSourceWorkflow** - Crawl a single source
2. **BulkCrawlWorkflow** - Crawl multiple sources in parallel
3. **ScheduledMaintenanceWorkflow** - Clean duplicates, update embeddings, generate stats
4. **ContinuousCrawlWorkflow** - Continuous crawling with periodic updates

### API Endpoints

Worker management endpoints (when `USE_TEMPORAL=true`):

- `POST /api/v1/worker/crawl` - Trigger crawl
- `POST /api/v1/worker/maintenance` - Run maintenance
- `GET /api/v1/worker/sources` - List available sources

### Using Workflows

Example: Trigger a crawl

```bash
curl -X POST http://localhost:8080/api/v1/worker/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "source": "cyberleninka",
    "limit": 50
  }'
```

Example: Bulk crawl

```bash
curl -X POST http://localhost:8080/api/v1/worker/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "sources": ["cyberleninka", "arxiv", "elibrary"],
    "limit": 30
  }'
```

## Railway + Temporal Cloud

For production Temporal:

1. **Sign up for Temporal Cloud** (https://cloud.temporal.io)

2. **Get connection details** (host, namespace, certificates)

3. **Update Railway variables:**
   ```bash
   railway variables set TEMPORAL_HOST=your-namespace.tmprl.cloud:7233
   railway variables set TEMPORAL_NAMESPACE=your-namespace
   railway variables set TEMPORAL_TLS_CERT="-----BEGIN CERTIFICATE-----..."
   railway variables set TEMPORAL_TLS_KEY="-----BEGIN PRIVATE KEY-----..."
   railway variables set USE_TEMPORAL=true
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

## Troubleshooting

### SSL Issues Locally
If you get `SSLCertVerificationError` on macOS:
- Use Docker Compose (recommended)
- Or deploy to Railway

### Database Connection
Check `DATABASE_URL` is set correctly:
```bash
railway variables
```

### Health Check Failing
Increase healthcheck timeout in `railway.json`:
```json
"healthcheckTimeout": 300
```

### Migration Failures
Check Alembic is up to date:
```bash
railway run alembic current
railway run alembic upgrade head
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `USE_SQLITE` | Use SQLite instead of PostgreSQL | false |
| `USE_TEMPORAL` | Enable Temporal worker | false |
| `TEMPORAL_HOST` | Temporal server address | localhost:7233 |
| `TEMPORAL_NAMESPACE` | Temporal namespace | default |
| `SEED_DATABASE` | Load sample data on startup | false |
| `PORT` | Server port | 8000 |

## Architecture

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────────┐
│   React Frontend │────▶│  FastAPI    │────▶│   PostgreSQL    │
│   (Port 3000)    │     │  (Port 8000)│     │  + pgvector     │
└─────────────────┘     └──────┬──────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │   Temporal  │
                        │   (Optional)│
                        └─────────────┘
```

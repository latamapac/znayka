# Temporal.io Integration

## Overview

Temporal.io provides durable execution for the crawler orchestration, ensuring:
- **Reliability** - Automatic retries on failures
- **Observability** - Full workflow history and visibility
- **Scheduling** - Periodic crawls and maintenance
- **Scalability** - Parallel execution across sources

## Workflows

### 1. CrawlSourceWorkflow
Crawls a single academic source.

```python
# Trigger via API
POST /api/v1/worker/crawl
{
  "source": "cyberleninka",
  "query": "machine learning",
  "limit": 50
}
```

### 2. BulkCrawlWorkflow
Crawls multiple sources in parallel.

```python
POST /api/v1/worker/crawl
{
  "query": "artificial intelligence",
  "sources": ["cyberleninka", "arxiv", "elibrary"],
  "limit": 30
}
```

### 3. ScheduledMaintenanceWorkflow
Runs maintenance tasks:
- Clean duplicate papers
- Update missing embeddings
- Generate database statistics

```python
POST /api/v1/worker/maintenance
```

### 4. ContinuousCrawlWorkflow
Continuous crawling with periodic updates.

```python
POST /api/v1/worker/schedule-continuous
{
  "queries": ["machine learning", "AI", "data science"],
  "sources": ["cyberleninka", "arxiv"],
  "interval_hours": 24
}
```

## Local Development

### Option 1: Docker Compose (Recommended)

```bash
docker-compose up -d temporal temporal-ui
```

Access Temporal UI at http://localhost:8233

### Option 2: Manual Setup

```bash
# Install temporal-cli
curl -sSf https://temporal.download/cli.sh | sh

# Start temporal server
temporal server start-dev
```

## Configuration

Environment variables:

```bash
USE_TEMPORAL=true              # Enable Temporal integration
TEMPORAL_HOST=localhost:7233   # Temporal server address
TEMPORAL_NAMESPACE=default     # Temporal namespace
```

## Worker Management

### Start Worker
```bash
# In Docker Compose, worker starts automatically
# Or manually:
python -m app.temporal.worker
```

### Check Workflow Status

Via Temporal UI (http://localhost:8233) or API:

```bash
# List running workflows
temporal workflow list

# Describe specific workflow
temporal workflow describe --workflow-id <id>
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Temporal  │────▶│   Worker    │
│   (API)     │     │   Server    │     │  (Backend)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Crawlers   │
                                        │  Database   │
                                        └─────────────┘
```

## Retry Policies

All workflows have retry policies:
- **Maximum attempts**: 2-3
- **Initial interval**: 10 seconds
- **Exponential backoff**: Yes

## Error Handling

Failed activities are retried automatically. After max retries:
- Workflow continues with partial results
- Failed tasks are logged
- Manual intervention possible via UI

## Production: Temporal Cloud

For production, use Temporal Cloud:

1. Sign up at https://cloud.temporal.io
2. Get namespace and certificates
3. Configure environment:

```bash
TEMPORAL_HOST=your-namespace.tmprl.cloud:7233
TEMPORAL_NAMESPACE=your-namespace
TEMPORAL_TLS_CERT=-----BEGIN CERTIFICATE-----
TEMPORAL_TLS_KEY=-----BEGIN PRIVATE KEY-----
```

## Benefits Over Celery

| Feature | Celery | Temporal |
|---------|--------|----------|
| Retries | Basic | Durable with backoff |
| Visibility | Limited logs | Full workflow history |
| Debugging | Hard | Time-travel debugging |
| Scheduling | Cron | Native schedule API |
| State | In-memory | Persisted |
| Scalability | Good | Excellent |

## Troubleshooting

### Worker not starting
```bash
# Check Temporal server
nc -zv localhost 7233

# Check logs
docker-compose logs temporal-worker
```

### Workflow stuck
```bash
# Check workflow status
temporal workflow list --open

# Terminate stuck workflow
temporal workflow terminate --workflow-id <id>
```

### Connection refused
Ensure `TEMPORAL_HOST` matches your setup:
- Docker Compose: `temporal:7233`
- Local: `localhost:7233`
- Cloud: `namespace.tmprl.cloud:7233`

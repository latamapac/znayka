# Railway Deployment - Metadata Only

## Quick Deploy

```bash
cd /Users/mark/russian-science-hub
./deploy-railway.sh
```

## Manual Steps

```bash
cd backend

# 1. Login
railway login

# 2. Init project
railway init

# 3. Add PostgreSQL
railway add --database postgres

# 4. Deploy
railway up

# 5. Migrations
railway run "alembic upgrade head"
```

## Environment Variables (auto-set)

| Variable | Value |
|----------|-------|
| `USE_SQLITE` | false |
| `USE_TEMPORAL` | false |
| `SEED_DATABASE` | true (first time) |

## After Deploy

```bash
# Get URL
railway status

# View logs
railway logs

# Disable seeding after first deploy
railway variables set SEED_DATABASE=false
```

## What's Included

✅ **Metadata**: title, abstract, authors, keywords, citations, source URLs  
❌ **No PDF downloads**: Only links to original PDFs

## API Endpoints

```
GET  /health
GET  /api/v1/papers/search?q=...
GET  /api/v1/sources/list
GET  /api/v1/sources/stats
```

## Next: Crawlers on Railway

After deploy, crawlers can run on Railway without SSL issues:

```bash
# SSH into Railway instance
railway ssh

# Run crawler
python -m crawlers.orchestrator --query "machine learning" --limit 100
```

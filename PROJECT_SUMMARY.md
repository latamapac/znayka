# ZNAYKA - Project Summary

## ✅ What's Included

### Backend (FastAPI)
- ✅ FastAPI REST API with auto-generated docs (`/docs`)
- ✅ PostgreSQL + pgvector for vector similarity search
- ✅ SQLAlchemy 2.0 with async support
- ✅ Alembic migrations
- ✅ Celery + Redis for background tasks
- ✅ Sentence Transformers for embeddings (local)
- ✅ OpenAI API support (optional)
- ✅ Unique indexing system: `RSH-{SOURCE}-{YEAR}-{SEQUENCE}`

### Frontend (React + TypeScript)
- ✅ React 18 with TypeScript
- ✅ Tailwind CSS for styling
- ✅ TanStack Query for data fetching
- ✅ Zustand for state management
- ✅ Responsive design
- ✅ Pages: Home, Search, Paper Detail, Stats, About

### Crawlers (9 Sources)
1. ✅ eLibrary.ru (РИНЦ)
2. ✅ CyberLeninka
3. ✅ arXiv
4. ✅ РГБ Диссертации (diss.rsl.ru)
5. ✅ НЭБ (rusneb.ru)
6. ✅ ИНИОН РАН
7. ✅ ВШЭ Наукометрика
8. ✅ Президентская библиотека (prlib.ru)
9. ✅ Росстат/ЕМИСС

### Deployment
- ✅ Docker + Docker Compose
- ✅ Railway deployment ready
- ✅ GitHub Actions CI/CD
- ✅ Makefile commands

### Documentation
- ✅ API documentation
- ✅ Architecture docs
- ✅ Deployment guides (Docker + Railway)

## 🗂️ Project Structure

```
russian-science-hub/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # REST endpoints
│   │   ├── core/              # Config
│   │   ├── db/                # Database
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── tasks/             # Celery tasks
│   │   └── main.py            # Entry point
│   ├── alembic/               # Migrations
│   ├── Dockerfile
│   ├── Procfile
│   ├── railway.json
│   └── requirements.txt
│
├── crawlers/                   # Paper ingestion
│   ├── sources/               # 9 crawler implementations
│   ├── orchestrator.py        # Crawler coordinator
│   └── base_crawler.py
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API client
│   │   └── types/             # TypeScript types
│   ├── Dockerfile
│   ├── railway.json
│   └── package.json
│
├── docs/                       # Documentation
│   ├── api/
│   ├── architecture/
│   └── deployment/
│
├── .github/workflows/          # CI/CD
│   ├── ci.yml
│   └── deploy-railway.yml
│
├── docker-compose.yml
├── Makefile
├── railway.json               # Root Railway config
└── README.md
```

## 🚀 Quick Start Commands

```bash
# Local with Docker
make setup

# Railway deployment
./scripts/deploy-railway.sh

# Or manually:
cd backend && railway up
cd frontend && railway up

# Crawl papers
make crawl q="machine learning" source=cyberleninka
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/papers/search` | Search papers (text/semantic/hybrid) |
| POST | `/api/v1/papers/semantic-search` | Semantic search |
| GET | `/api/v1/papers/{id}` | Get paper by ID |
| GET | `/api/v1/papers/{id}/similar` | Find similar papers |
| GET | `/api/v1/papers/stats/index` | Database statistics |
| GET | `/api/v1/sources/list` | List all sources |
| GET | `/health` | Health check |

## 🎯 Features

- 🔍 **Hybrid Search**: Full-text + semantic with RRF fusion
- 🧠 **Vector Embeddings**: 384-dim using sentence-transformers
- 🆔 **Unique IDs**: Format `RSH-ELIB-2024-00012345`
- 🌐 **Russian-focused**: Full Russian language support
- 📄 **PDF Support**: Links to full-text PDFs where available
- 📊 **Citation Tracking**: Citation counts from sources
- 🚀 **Auto-scaling**: Railway deployment ready

## 📦 Services

| Service | Tech | Port |
|---------|------|------|
| Backend | FastAPI + Python 3.12 | 8000 |
| Frontend | React + Vite | 5173 |
| Database | PostgreSQL 15 + pgvector | 5432 |
| Cache/Queue | Redis | 6379 |
| Worker | Celery | - |

## 🔐 Environment Variables

```bash
# Required
DATABASE_URL=postgresql+asyncpg://...
SECRET_KEY=your-secret-key

# Optional
OPENAI_API_KEY=sk-...      # For better embeddings
REDIS_URL=redis://...      # For caching/tasks
CORS_ORIGINS=...           # Frontend URLs
```

## 📝 Next Steps

1. ✅ Deploy to Railway (`./scripts/deploy-railway.sh`)
2. ✅ Set environment variables in Railway dashboard
3. ✅ Run database migrations
4. ✅ Start crawling papers
5. ✅ Share with students!

## 📊 Stats Tracking

The system tracks:
- Total papers indexed
- Papers by source
- Papers by year
- Papers with full text
- Processing coverage %

---

**Status**: ✅ Ready for deployment
**Total Files**: 62
**Sources**: 9 crawlers
**Stack**: Python + React + PostgreSQL + Redis + Docker + Railway

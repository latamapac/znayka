# Russian Science Hub (Российский Научный Хаб)

A comprehensive academic paper database and search platform for Russian scientific research. This project aims to aggregate, index, and make searchable all academic papers from Russian universities, research institutions, and academic journals.

## 🎯 Mission

Create a unified, open-access platform where:
- Students can find relevant research papers
- Researchers can discover related work
- Academics can track citations and trends
- Anyone can ask questions and get paper recommendations

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Crawlers  │────▶│  PostgreSQL │────▶│  Vector Search  │
│  (Sources)  │     │  + pgvector │     │   (Embeddings)  │
└─────────────┘     └─────────────┘     └─────────────────┘
                                                │
┌─────────────┐     ┌─────────────┐            │
│   React     │◀────│  FastAPI    │◀───────────┘
│  Frontend   │     │   Backend   │
└─────────────┘     └─────────────┘
```

## 📁 Project Structure

```
russian-science-hub/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── core/      # Config, security
│   │   ├── db/        # Database connection
│   │   ├── models/    # SQLAlchemy models
│   │   ├── services/  # Business logic
│   │   └── utils/     # Utilities
│   ├── alembic/       # Database migrations
│   └── requirements.txt
├── frontend/          # React frontend
├── crawlers/          # Paper ingestion system
│   ├── sources/       # Source-specific crawlers
│   ├── parsers/       # PDF/HTML parsers
│   └── processors/    # Text processing
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with pgvector extension
- Node.js 20+

### Option 1: Railway (Recommended) - One Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-url)

Or manually:
```bash
# 1. Install Railway CLI
npm install -g @railway/cli
railway login

# 2. Deploy backend
cd backend
railway init
railway add --database postgres
railway up

# 3. Run migrations
railway run "alembic upgrade head"

# 4. Deploy frontend (new service)
cd ../frontend
railway init --service frontend
railway up
```

### Option 2: Docker Compose (Local)

```bash
# Clone and setup
git clone <repo-url>
cd russian-science-hub

# Start all services
make setup

# Or manually:
docker-compose up --build -d
make migrate
```

### Option 3: Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database
createdb russia_science_hub
psql -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📚 Data Sources

### Russian Academic Sources
- **eLibrary.ru** - Russian Science Citation Index
- **RSCI** - Russian Science Citation Index
- **CyberLeninka** - Open access Russian journals
- **KiberLeninka** - Scientific articles repository
- **Russian Academy of Sciences** - Publications
- **University Repositories**:
  - Moscow State University (MSU)
  - Saint Petersburg State University (SPbU)
  - MISIS
  - MIPT
  - HSE (Higher School of Economics)
  - And 100+ other universities

### International with Russian Authors
- **Google Scholar** - Cross-reference Russian authors
- **arXiv** - Physics, math, CS papers
- **Semantic Scholar** - General academic

## 🔍 Features

### Core Features
- ✅ **Universal Search** - Full-text + semantic search
- ✅ **Smart Indexing** - Unique DOI-based identifiers
- ✅ **Citation Tracking** - Track paper citations
- ✅ **Author Profiles** - Aggregate author works
- ✅ **PDF Storage** - Local archive of papers
- ✅ **API Access** - RESTful API for integrations

### Advanced Features
- 🤖 **AI Q&A** - Ask questions about papers
- 🔗 **Similar Papers** - Find related research
- 📊 **Trend Analysis** - Research trend visualization
- 🏷️ **Auto-tagging** - ML-based subject classification
- 🌍 **Multi-language** - Russian + English support
- ⚙️ **Temporal Workflows** - Robust crawler orchestration with retries and scheduling

## 🔐 Unique Indexing System

Each paper gets a unique identifier:
```
RSH-{SOURCE}-{YEAR}-{SEQUENCE}

Example: RSH-ELIB-2024-00012345
```

Where:
- `RSH` - Russian Science Hub prefix
- `ELIB` - Source code (eLibrary)
- `2024` - Publication year
- `00012345` - Sequential ID

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **pgvector** - Vector similarity search
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Celery** - Background tasks
- **Temporal.io** - Workflow orchestration (optional)
- **Redis** - Caching & task queue

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **TanStack Query** - Data fetching
- **Zustand** - State management

### ML/NLP
- **Sentence Transformers** - Text embeddings
- **OpenAI API** - Q&A and summarization
- **scikit-learn** - Classification

## 📖 API Documentation

API documentation is available at `/docs` when running the backend.

### Main Endpoints

```http
# Search papers
GET /api/v1/papers/search?q=machine+learning&limit=20

# Get paper by ID
GET /api/v1/papers/{paper_id}

# Semantic search
POST /api/v1/papers/semantic-search
{
  "query": "нейронные сети для обработки текста",
  "limit": 10
}

# Ask question about papers
POST /api/v1/qa/ask
{
  "question": "Какие последние достижения в квантовых вычислениях в России?"
}
```

## 📦 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions including:
- Railway deployment (recommended for production)
- Docker Compose setup (local development)
- Temporal.io integration for crawler orchestration

## 🤝 Contributing

This is a student project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Russian Ministry of Science and Education
- CyberLeninka for open access initiative
- All contributing universities and researchers

---

**Made with ❤️ by Russian students for Russian science**

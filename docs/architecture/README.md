# Russian Science Hub - Architecture

## Overview

Russian Science Hub is a distributed system designed to aggregate, index, and search academic papers from multiple Russian and international sources.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  React Frontend (Port 5173)                                                  │
│  ├── Search Interface                                                        │
│  ├── Paper Browser                                                          │
│  └── Admin Dashboard                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8000)                                                 │
│  ├── REST API Endpoints                                                     │
│  ├── Search Service (Text + Semantic)                                       │
│  ├── Indexing Service                                                       │
│  └── Embeddings Service                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PostgreSQL   │  │ Redis        │  │ Object       │  │ Celery       │    │
│  │ + pgvector   │  │ Cache/Queue  │  │ Storage      │  │ Workers      │    │
│  │              │  │              │  │ (PDFs)       │  │              │    │
│  │ - Papers     │  │              │  │              │  │ - Crawling   │    │
│  │ - Authors    │  │              │  │              │  │ - Embeddings │    │
│  │ - Citations  │  │              │  │              │  │ - Indexing   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CRAWLER LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ eLibrary     │  │ CyberLeninka │  │ arXiv        │  │ University   │    │
│  │ Crawler      │  │ Crawler      │  │ Crawler      │  │ Crawlers     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Paper Ingestion

```
External Source → Crawler → Data Normalization → Database
     ↓              ↓             ↓                ↓
  eLibrary     Async HTTP    PaperData         Store
  CyberLeninka   Fetch       Schema           Metadata
  arXiv                      Transform        Embeddings
```

### 2. Search Flow

```
User Query → Search API → Query Processing → Database
                 ↓              ↓                ↓
           Parse Params    Text Search    PostgreSQL
                           Vector Search   pgvector
                           Hybrid Merge
```

### 3. Embedding Generation

```
Paper Text → Embedding Service → Vector Store
     ↓              ↓                ↓
  Title      Local Model       PostgreSQL
  Abstract   or OpenAI         pgvector
```

## Database Schema

### Papers Table

```sql
┌─────────────────────┬─────────────────┬────────────────────────────────┐
│ Column              │ Type            │ Description                    │
├─────────────────────┼─────────────────┼────────────────────────────────┤
│ id                  │ VARCHAR(32) PK  │ RSH-{SRC}-{YR}-{SEQ}          │
│ title               │ TEXT            │ Paper title                    │
│ title_ru            │ TEXT            │ Russian title                  │
│ abstract            │ TEXT            │ Abstract                       │
│ abstract_ru         │ TEXT            │ Russian abstract               │
│ doi                 │ VARCHAR(256)    │ Digital Object Identifier      │
│ arxiv_id            │ VARCHAR(50)     │ arXiv identifier               │
│ source_type         │ VARCHAR(50)     │ eLibrary, CyberLeninka, etc.   │
│ publication_year    │ INTEGER         │ Year of publication            │
│ title_embedding     │ VECTOR(384)     │ Title vector embedding         │
│ abstract_embedding  │ VECTOR(384)     │ Abstract vector embedding      │
│ ...                 │ ...             │ ...                            │
└─────────────────────┴─────────────────┴────────────────────────────────┘
```

### Authors Table

```sql
┌─────────────────────┬─────────────────┬────────────────────────────────┐
│ Column              │ Type            │ Description                    │
├─────────────────────┼─────────────────┼────────────────────────────────┤
│ id                  │ VARCHAR(32) PK  │ Unique author ID              │
│ full_name           │ VARCHAR(300)    │ Author full name              │
│ full_name_ru        │ VARCHAR(300)    │ Russian name                  │
│ orcid               │ VARCHAR(50)     │ ORCID identifier              │
│ affiliations        │ ARRAY(TEXT)     │ List of affiliations          │
└─────────────────────┴─────────────────┴────────────────────────────────┘
```

### Paper-Author Association

```sql
┌─────────────────────┬─────────────────┬────────────────────────────────┐
│ Column              │ Type            │ Description                    │
├─────────────────────┼─────────────────┼────────────────────────────────┤
│ paper_id            │ VARCHAR(32) FK  │ Reference to papers           │
│ author_id           │ VARCHAR(32) FK  │ Reference to authors          │
└─────────────────────┴─────────────────┴────────────────────────────────┘
```

## Unique Indexing System

### ID Format

```
RSH-{SOURCE_CODE}-{YEAR}-{SEQUENCE}

Example: RSH-ELIB-2024-00012345
```

### Source Codes

| Source        | Code | Example ID              |
|---------------|------|-------------------------|
| eLibrary      | ELIB | RSH-ELIB-2024-00000001 |
| CyberLeninka  | CYBL | RSH-CYBL-2024-00000001 |
| arXiv         | ARXV | RSH-ARXV-2024-00000001 |
| Manual Entry  | MANL | RSH-MANL-2024-00000001 |

## Search Architecture

### Hybrid Search (Default)

1. **Full-text Search** - PostgreSQL ILIKE on title, abstract, keywords
2. **Vector Search** - pgvector cosine similarity on embeddings
3. **RRF Fusion** - Reciprocal Rank Fusion to combine results

### Semantic Search

1. Generate query embedding using Sentence Transformers
2. Find nearest neighbors using pgvector
3. Return results ordered by similarity

## Scaling Strategy

### Horizontal Scaling

```
                    ┌─────────────┐
                    │   Load      │
                    │  Balancer   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Backend   │  │  Backend   │  │  Backend   │
    │   Pod 1    │  │   Pod 2    │  │   Pod N    │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │  Primary    │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
            ┌──────────┐  ┌──────────┐
            │  Read    │  │  Read    │
            │ Replica  │  │ Replica  │
            └──────────┘  └──────────┘
```

### Caching Strategy

1. **Redis Cache** - Search results, paper metadata
2. **CDN** - Static assets, PDF files
3. **Database Query Cache** - Frequent queries

## Security Architecture

### Authentication (Future)

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────▶│  API GW  │────▶│  Auth    │
└──────────┘     └──────────┘     │ Service  │
                                  └──────────┘
```

### Data Protection

1. **Database** - Encryption at rest
2. **Network** - TLS 1.3 for all communications
3. **API** - Rate limiting, input validation
4. **Storage** - Encrypted PDF storage

## Monitoring

### Metrics

- Search latency (p50, p95, p99)
- Indexing throughput
- Database connections
- Cache hit rate
- Crawler success rate

### Logging

```
[2024-01-01 12:00:00] INFO search query="ML" results=50 time=150ms
[2024-01-01 12:00:01] INFO indexed paper_id=RSH-ELIB-2024-00000001
[2024-01-01 12:00:02] ERROR crawler elibrary failed: timeout
```

## Future Enhancements

1. **Graph Database** - Citation networks
2. **Recommendation Engine** - Personalized paper suggestions
3. **Real-time Indexing** - Webhook-based updates
4. **Multi-language Support** - Chinese, German, etc.
5. **Federated Search** - Query external APIs directly

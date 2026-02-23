# ZNAYKA National-Level Architecture
## From Prototype to Production-Scale Platform

---

## 🚨 Current vs Required Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT (Demo/PoC)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Database:    PostgreSQL (single instance, 10K-100K papers)               │
│   Search:      SQL LIKE queries (slow for millions)                         │
│   Sources:     9 sources                                                  │
│   Validation:  None (mock data acceptable)                                  │
│   Scale:       Single region, single crawler                                │
│   Users:       No auth, no personalization                                  │
│                                                                             │
│   GOOD FOR:    Demo, testing, small scale                                   │
│   NOT FOR:     National platform, millions of papers, real users            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    NATIONAL-LEVEL (Production)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Database:    ClickHouse (columnar, billions of rows)                      │
│   Search:      Elasticsearch/OpenSearch (sub-second full-text)             │
│   Cache:       Redis (frequently accessed data)                             │
│   Queue:       Apache Kafka (crawl jobs, processing pipeline)              │
│   Sources:     50+ sources (global coverage)                               │
│   Validation:  Temporal workflows (data quality, language check)           │
│   Scale:       Multi-region, distributed crawlers                          │
│   Users:       Auth, personalization, analytics                            │
│   Monitoring:  Real-time metrics, alerting                                 │
│                                                                             │
│   GOOD FOR:    National platform, millions of users, billions of papers    │
│   COMPARABLE:  Google Scholar, Semantic Scholar, eLibrary                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Required Architecture Components

### 1. DATABASE LAYER: ClickHouse

**Why ClickHouse?**
- Columnar storage (100x faster for analytics)
- Billions of rows, real-time inserts
- Built-in full-text search
- Compression (10x less storage)
- Distributed (sharding across nodes)

```sql
-- ClickHouse Schema Example
CREATE TABLE papers (
    id String,
    title String,
    abstract String,
    authors Array(String),
    source LowCardinality(String),
    language LowCardinality(String),
    year UInt16,
    citations UInt32,
    keywords Array(String),
    pdf_url String,
    pdf_storage_path String,
    full_text String,
    crawled_at DateTime,
    -- Vector embedding for semantic search
    embedding Array(Float32),
    
    INDEX idx_title title TYPE full_text,
    INDEX idx_abstract abstract TYPE full_text
) ENGINE = MergeTree()
ORDER BY (source, year, id);

-- Materialized view for analytics
CREATE MATERIALIZED VIEW papers_by_source
ENGINE = SummingMergeTree()
ORDER BY (source, year)
AS SELECT 
    source,
    year,
    count() as paper_count,
    sum(citations) as total_citations
FROM papers
GROUP BY source, year;
```

**vs PostgreSQL:**
| Metric | PostgreSQL | ClickHouse |
|--------|-----------|------------|
| 1M papers insert | 5 minutes | 10 seconds |
| Aggregation query | 30 seconds | 0.1 seconds |
| Storage | 100GB | 10GB (compressed) |
| Full-text search | Slow | Fast (inverted index) |
| Scale | Single node | Distributed cluster |

---

### 2. SEARCH LAYER: Elasticsearch/OpenSearch

**Why Elasticsearch?**
- Sub-second full-text search
- Faceted search (filter by year, source, author)
- Autocomplete/suggestions
- Relevance scoring
- Synonyms, stemming

```
Search Features Required:
├── Full-text search (title, abstract, keywords)
├── Fuzzy search (typo tolerance)
├── Faceted filters (year, source, author, language)
├── Autocomplete (query suggestions)
├── Semantic search (vector similarity)
├── Highlighting (show matching terms)
└── Aggregations (stats, histograms)
```

---

### 3. QUEUE SYSTEM: Apache Kafka

**Why Kafka?**
- Handle 100K+ messages/second
- Persist crawl jobs
- Process papers asynchronously
- Multiple consumers (download PDF, analyze, index)

```
Kafka Topics:
├── crawler.jobs (crawl requests)
├── crawler.results (crawled papers)
├── pdf.download (PDF download queue)
├── pdf.completed (downloaded PDFs)
├── validation.pending (data quality check)
├── validation.failed (failed validation)
├── search.index (papers to index in ES)
└── analytics.events (user interactions)
```

---

### 4. CACHING: Redis Cluster

**Cache Strategy:**
```
Hot Data (Redis):
├── Popular searches (top 1000 queries)
├── Paper details (frequently accessed)
├── Author profiles
├── Homepage stats
└── API rate limit counters

TTL Strategy:
├── Search results: 5 minutes
├── Paper details: 1 hour
├── Stats: 10 minutes
└── User sessions: 24 hours
```

---

### 5. TEMPORAL WORKFLOWS: Data Quality Pipeline

**Why Temporal?**
- Reliable long-running workflows
- Retry logic for failed steps
- State management
- Visibility into processing

```python
@workflow.defn
class PaperValidationWorkflow:
    """Validates paper data quality"""
    
    @workflow.run
    async def run(self, paper_id: str):
        # Step 1: Language detection
        detected_lang = await workflow.execute_activity(
            detect_language,
            paper_id,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 2: Validate against claimed language
        paper = await workflow.execute_activity(
            get_paper,
            paper_id
        )
        
        if detected_lang != paper['language']:
            await workflow.execute_activity(
                flag_language_mismatch,
                paper_id,
                detected_lang
            )
        
        # Step 3: Check for duplicates
        duplicates = await workflow.execute_activity(
            find_duplicates,
            paper_id,
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        if duplicates:
            await workflow.execute_activity(
                merge_duplicates,
                paper_id,
                duplicates
            )
        
        # Step 4: Validate PDF (if available)
        if paper.get('pdf_url'):
            await workflow.execute_activity(
                validate_pdf,
                paper_id,
                start_to_close_timeout=timedelta(minutes=5)
            )
        
        # Step 5: Update search index
        await workflow.execute_activity(
            index_in_elasticsearch,
            paper_id
        )
```

**Validation Checks:**
1. **Language Detection**: Verify title/abstract matches claimed language
2. **Duplicate Detection**: Same paper from multiple sources
3. **PDF Validation**: Corrupt PDFs, wrong format
4. **Metadata Completeness**: Required fields present
5. **Spam Detection**: Low-quality/junk papers
6. **Citation Validation**: Real citations, not fabricated

---

### 6. EXPANDED SOURCES (50+)

**Current (9):**
arXiv, CyberLeninka, eLibrary, RUSNEB, RSL, INION, HSE, Presidential, Rosstat

**Required (50+):**
```
Russia/CIS (20 sources):
├── eLibrary.ru (main citation index)
├── CyberLeninka (open access)
├── RSCI (Russian Science Citation Index)
├── DisserCat (dissertations)
├── ISTINA (MSU research)
├── KiberLeninka
├── NLR (National Library of Russia)
├── Belarusian academic resources
├── Ukrainian academic resources
└── etc.

International (30+ sources):
├── PubMed (medical)
├── IEEE Xplore (engineering)
├── Springer (journals)
├── ScienceDirect (Elsevier)
├── Wiley Online Library
├── Nature / Springer
├── ACM Digital Library
├── JSTOR (humanities)
├── Google Scholar (aggregator)
├── Semantic Scholar (AI-focused)
├── Microsoft Academic
├── CrossRef (DOI resolver)
├── ORCID (author profiles)
├── Unpaywall (open access finder)
├── DOAJ (open access journals)
├── CORE (research papers aggregator)
├── BASE (Bielefeld Academic Search)
├── OpenAlex (open academic graph)
└── etc.
```

---

### 7. MONITORING & OBSERVABILITY

**Metrics to Track:**
```
System Metrics:
├── Database: QPS, latency, connections
├── Search: Query time, cache hit rate
├── Crawlers: Papers/minute, error rate
├── Queue: Lag, consumer lag
└── API: Response time, error rate

Business Metrics:
├── Total papers (by source, by language)
├── Search queries (popular terms)
├── User engagement (searches per user)
├── PDF downloads
├── Crawler coverage (% of target sources)
└── Data quality (validation pass rate)

Alerting:
├── Crawler down for >1 hour
├── Database connections maxed
├── Search latency >500ms
├── Queue lag >10K messages
├── Error rate >1%
└── Disk space >80%
```

**Tools:**
- Prometheus (metrics collection)
- Grafana (dashboards)
- Jaeger (distributed tracing)
- Sentry (error tracking)
- PagerDuty (alerts)

---

### 8. USER MANAGEMENT & PERSONALIZATION

**Features Required:**
```
Authentication:
├── Email/password login
├── OAuth (Google, ORCID)
├── Institution login (Shibboleth/SAML)
└── API keys for researchers

User Features:
├── Saved searches (email alerts)
├── Paper collections (folders)
├── Citation management (export to Zotero, Mendeley)
├── Reading history
├── Recommended papers (ML-based)
├── Author following (new papers alert)
└── Institution dashboard

Analytics (per user):
├── Search history
├── Downloaded papers
├── Saved queries
└── Citation exports
```

---

### 9. API & RATE LIMITING

**API Design:**
```
Public API:
GET /api/v1/papers/search?q={query}&page={n}
GET /api/v1/papers/{id}
GET /api/v1/authors/{id}
GET /api/v1/sources
GET /api/v1/stats

Rate Limits:
├── Anonymous: 100 req/hour
├── Registered: 1000 req/hour
├── Premium: 10000 req/hour
└── Institutional: Unlimited

Authentication:
├── API Key (header: X-API-Key)
├── OAuth 2.0
└── JWT tokens
```

---

### 10. DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOAD BALANCER                                   │
│                         (NGINX / Cloudflare)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐           ┌────────▼────────┐           ┌────────▼────────┐
│   WEB SERVER   │           │   WEB SERVER    │           │   WEB SERVER    │
│   (Next.js)    │           │   (Next.js)     │           │   (Next.js)     │
└───────┬────────┘           └────────┬────────┘           └────────┬────────┘
        │                             │                              │
        └─────────────────────────────┼──────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                           API GATEWAY                                        │
│                      (Kong / Ambassador)                                     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼──────────────────────────────┐
        │                             │                              │
┌───────▼────────┐           ┌────────▼────────┐           ┌────────▼────────┐
│  API SERVER    │           │  API SERVER     │           │  API SERVER     │
│  (FastAPI)     │           │  (FastAPI)      │           │  (FastAPI)      │
└───────┬────────┘           └────────┬────────┘           └────────┬────────┘
        │                             │                              │
        │         ┌───────────────────┼───────────────────┐          │
        │         │                   │                   │          │
┌───────▼─────────▼────────┐ ┌────────▼────────┐ ┌────────▼─────────▼────────┐
│         REDIS            │ │   ELASTICSEARCH │ │       CLICKHOUSE          │
│       (Cache/Queue)      │ │     (Search)    │ │       (Analytics DB)      │
└──────────────────────────┘ └─────────────────┘ └───────────────────────────┘
        │                             │                              │
        └─────────────────────────────┼──────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                         KAFKA CLUSTER                                       │
│                    (Crawl Jobs, Processing)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼──────────────────────────────┐
        │                             │                              │
┌───────▼────────┐           ┌────────▼────────┐           ┌────────▼────────┐
│   CRAWLER 1    │           │   CRAWLER 2     │           │   CRAWLER N     │
│  (arXiv, etc)  │           │  (eLibrary,etc) │           │  (Other sources)│
└────────────────┘           └─────────────────┘           └─────────────────┘
```

---

## 📊 Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Deploy ClickHouse cluster
- [ ] Set up Elasticsearch
- [ ] Configure Kafka
- [ ] Deploy Redis cluster
- [ ] Basic API with new stack

### Phase 2: Data Pipeline (Weeks 3-4)
- [ ] Temporal workflows for validation
- [ ] Kafka producers (crawlers)
- [ ] Kafka consumers (processors)
- [ ] Data migration from PostgreSQL

### Phase 3: Search & API (Weeks 5-6)
- [ ] Elasticsearch indexing pipeline
- [ ] Search API endpoints
- [ ] Autocomplete
- [ ] Faceted search

### Phase 4: Scale Sources (Weeks 7-8)
- [ ] Add 20 more sources
- [ ] Distributed crawler deployment
- [ ] Source health monitoring

### Phase 5: User Features (Weeks 9-10)
- [ ] Authentication system
- [ ] User profiles
- [ ] Saved searches
- [ ] Email alerts

### Phase 6: Polish (Weeks 11-12)
- [ ] Monitoring dashboards
- [ ] Performance optimization
- [ ] Load testing
- [ ] Documentation

---

## 💰 Cost Estimate (National Scale)

**Monthly Costs (1 billion papers, 1M users):**

| Component | Specs | Cost/Month |
|-----------|-------|-----------|
| ClickHouse | 5 nodes, 64GB RAM each | $2,000 |
| Elasticsearch | 3 nodes, 32GB RAM each | $1,500 |
| Kafka | 3 brokers, managed | $800 |
| Redis | Cluster, 16GB | $400 |
| Kubernetes | 20 nodes | $3,000 |
| Storage | 100TB (PDFs) | $2,000 |
| Bandwidth | 100TB/month | $5,000 |
| Monitoring | Datadog/Grafana | $500 |
| **TOTAL** | | **~$15,000/month** |

**Comparable to:**
- Google Scholar: ~$100K+/month (estimated)
- Semantic Scholar: ~$50K+/month (estimated)
- eLibrary: ~$30K+/month (estimated)

---

## 🎯 Summary: What You Need NOW

### Immediate (This Week):
1. **ClickHouse** - Replace PostgreSQL
2. **Elasticsearch** - Real search
3. **20 more sources** - Better coverage
4. **Temporal validation** - Data quality

### Next Month:
5. **Kafka queue** - Scalable pipeline
6. **Redis cache** - Fast API
7. **User auth** - Personalization
8. **Monitoring** - Production-ready

### Next Quarter:
9. **50+ sources** - Global coverage
10. **ML recommendations** - User engagement
11. **Mobile app** - Accessibility
12. **Institutional features** - University integrations

---

## 🚀 Next Steps

**Want me to implement the ClickHouse + Elasticsearch architecture now?**

This requires:
1. Deploy ClickHouse cluster
2. Deploy Elasticsearch
3. Update crawlers to write to ClickHouse
4. Set up Temporal for validation
5. Add 20 more sources
6. Migrate data

**Time:** 2-3 weeks for full implementation
**Cost:** ~$500/month to start, scale to $15K/month for national level

**Or start smaller?**
- Just ClickHouse + more sources (~$100/month)
- Add Elasticsearch later
- Add Temporal validation later

What would you like to do?
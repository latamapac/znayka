# ZNAYKA Architecture & PDF Strategy

## Current vs Real Implementation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CURRENT (Mock Data)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Frontend ──► Backend ──► MOCK_PAPERS (10,000 fake)                        │
│                                ↓                                            │
│                           Filter in Python memory                           │
│                                                                             │
│   Pros:                                                                     │
│   - Works immediately                                                       │
│   - No database needed                                                      │
│   - Fast for testing UI                                                     │
│                                                                             │
│   Cons:                                                                     │
│   - All titles look similar (generated)                                     │
│   - Authors are random names                                                │
│   - No real PDFs                                                            │
│   - Can't scale beyond memory limits                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        REAL IMPLEMENTATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Frontend ──► Backend ──► PostgreSQL + pgvector                            │
│                                ↓                                            │
│                        Real Crawlers (arXiv, eLibrary...)                   │
│                                ↓                                            │
│                        PDF Storage (Cloudflare R2)                          │
│                                                                             │
│   Pros:                                                                     │
│   - Real paper titles, authors, abstracts                                   │
│   - Actual downloadable PDFs                                                │
│   - Scales to millions of papers                                            │
│   - Full-text search with embeddings                                        │
│                                                                             │
│   Cons:                                                                     │
│   - Requires PostgreSQL database                                            │
│   - PDF storage costs money                                                 │
│   - Slower initial setup                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## PDF Download Strategy

### Why NOT Instant PDF Download?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PDF DOWNLOAD REALITY CHECK                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ONE PAPER:                                                                │
│   • Metadata:  ~2 KB (title, authors, abstract)                            │
│   • PDF:       ~2-10 MB (average 5 MB)                                      │
│                                                                             │
│   SCALE:                                                                    │
│   • 1,000 papers:  Metadata = 2 MB, PDFs = 5 GB                            │
│   • 100,000 papers: Metadata = 200 MB, PDFs = 500 GB                       │
│   • 1,000,000 papers: Metadata = 2 GB, PDFs = 5 TB                         │
│                                                                             │
│   COSTS (Cloudflare R2):                                                    │
│   • Storage: $0.015/GB/month                                                │
│   • 5 TB = $75/month just for storage                                       │
│   • Download bandwidth: $0.005/GB                                           │
│                                                                             │
│   TIME:                                                                     │
│   • Downloading 1 PDF: 2-10 seconds                                         │
│   • 1,000 papers: 30+ minutes                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended PDF Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SMART PDF HANDLING                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PHASE 1: Metadata First (Instant)                                         │
│   ─────────────────────────────────                                         │
│   • Download title, authors, abstract immediately                           │
│   • Store in PostgreSQL (fast, cheap)                                       │
│   • Paper becomes searchable instantly                                      │
│                                                                             │
│   PHASE 2: PDF On-Demand (Background)                                       │
│   ───────────────────────────────────                                       │
│   • PDF downloaded only when:                                               │
│     - User requests "Download PDF"                                          │
│     - OR paper is popular (many views)                                      │
│     - OR scheduled background job                                           │
│                                                                             │
│   PHASE 3: Priority Queue                                                   │
│   ─────────────────────                                                     │
│   • High priority: Recently viewed papers                                   │
│   • Medium priority: Papers from last crawl                                 │
│   • Low priority: Old papers, rarely accessed                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation: Switch to REAL Data

### Step 1: Create PostgreSQL Database

```bash
# Create Cloud SQL instance (one-time setup)
gcloud sql instances create znayka-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=europe-north1 \
  --storage-size=100GB \
  --availability-type=zonal

# Create database
gcloud sql databases create znayka --instance=znayka-db

# Set password
gcloud sql users set-password postgres \
  --instance=znayka-db \
  --password=YOUR_PASSWORD
```

### Step 2: Connect Backend to Real Database

```python
# backend/app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:PASSWORD@/znayka?host=/cloudsql/znayka-fresh-1771794343:europe-north1:znayka-db"
)

engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

### Step 3: Run Real Crawlers (Not Mock)

```bash
# Instead of simulate_crawl(), use actual crawlers:
from crawlers.sources.arxiv import ArxivCrawler
from crawlers.sources.cyberleninka import CyberleninkaCrawler

# Real arXiv API call
async with ArxivCrawler() as crawler:
    async for paper in crawler.search_papers("machine learning", limit=100):
        await store_paper_in_database(paper)
```

### Step 4: PDF Download Worker (Background)

```python
# background/pdf_downloader.py
async def download_pdf_worker():
    """Background worker that downloads PDFs on-demand"""
    while True:
        # Get papers without PDF
        papers = await get_papers_without_pdf(limit=10)
        
        for paper in papers:
            try:
                pdf_data = await download_pdf(paper.pdf_url)
                await store_pdf_in_r2(paper.id, pdf_data)
                await mark_pdf_downloaded(paper.id)
            except Exception as e:
                logger.error(f"Failed to download PDF for {paper.id}: {e}")
        
        # Wait before next batch
        await asyncio.sleep(60)
```

## Cost Estimates

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONTHLY COSTS (Real Implementation)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Cloud Run (Backend):           $10-50/month                               │
│   Cloud SQL (PostgreSQL):        $7-50/month                                │
│   R2 Storage (100K PDFs = 500GB): $7.50/month                               │
│   R2 Bandwidth (1TB downloads):  $5/month                                   │
│   Cloud Run Jobs (Crawler):      $20-100/month                              │
│                                                                             │
│   ─────────────────────────────────────────────────────                     │
│   TOTAL: ~$50-200/month for 100K papers with PDFs                           │
│                                                                             │
│   WITHOUT PDFs (metadata only):  ~$20-50/month                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Decision Guide

| You Want | Do This | Cost | Time to Setup |
|----------|---------|------|---------------|
| Demo/Testing | Keep mock data | Free | 0 min |
| Real metadata only | Deploy PostgreSQL + real crawlers | $20-50/mo | 30 min |
| Real metadata + some PDFs | Above + on-demand PDF download | $50-100/mo | 1 hour |
| Everything with all PDFs | Above + bulk PDF downloader | $100-200/mo | 2 hours |

## Recommendation for You

**Start with: Real metadata + on-demand PDFs**

```bash
# 1. Create database (one-time, 5 min)
gcloud sql instances create znayka-db --database-version=POSTGRES_15 --tier=db-f1-micro --region=europe-north1

# 2. Update backend to use real database (I can do this)

# 3. Deploy real crawlers (metadata only first)
./deploy-24-7-cloud.sh

# 4. Add PDF downloader later when needed
```

This gives you:
- ✅ Real paper titles, authors, abstracts
- ✅ Searchable in seconds
- ✅ Costs ~$30/month
- ✅ PDFs download on-demand when users click "Download"

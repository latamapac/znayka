# ZNAYKA Fast Crawler & 24/7 Cloud Deployment Guide

## Architecture Clarification

```
┌─────────────────┐      ┌──────────────────────────┐      ┌─────────────────┐
│   YOUR MACHINE  │──────▶│   GOOGLE CLOUD RUN       │◄─────│   24/7 CRAWLER  │
│   (Local)       │  API │   (Backend API)          │      │   (Cloud Job)   │
└─────────────────┘      └──────────────────────────┘      └─────────────────┘
         │                         │                                │
         │                  ┌──────┴──────┐                        │
         │                  │  PostgreSQL │                        │
         │                  │  + pgvector │                        │
         │                  └─────────────┘                        │
         │                                                         │
         ▼                                                         ▼
┌─────────────────┐      ┌──────────────────────────┐      ┌─────────────────┐
│  React Frontend │◄─────│   VERCEL (Frontend)      │      │  Continuous     │
│  (Browser)      │      │   znayka-frontend.       │      │  Crawling       │
└─────────────────┘      │   vercel.app             │      │  Job            │
                         └──────────────────────────┘      └─────────────────┘
```

**KEY POINT:** Running on YOUR machine only CALLS the cloud API. It doesn't run 24/7.
For true 24/7, you need to deploy the crawler TO THE CLOUD.

---

## Why Search Shows Limited Results

Currently, the backend returns MOCK DATA (only 3 papers). The crawlers simulate results but don't actually store papers in the database.

To get REAL searchable papers, you need to:
1. Deploy PostgreSQL database
2. Connect real crawlers that store data
3. Or use the mock data expansion below

---

## Option 1: Super Fast Local Crawler (For Demo)

### Generate 100,000 Mock Papers for Search

```bash
cd /Users/mark/russian-science-hub

# Run the fast mock data generator
python3 << 'PYEOF'
import json
import random
from datetime import datetime

SOURCES = ["arxiv", "cyberleninka", "elibrary", "rusneb", "rsl_dissertations", 
           "inion", "hse_scientometrics", "presidential_library", "rosstat_emiss"]

TOPICS = [
    "machine learning", "deep learning", "neural networks", "AI",
    "quantum computing", "blockchain", "cybersecurity", "cloud computing",
    "data science", "IoT", "robotics", "bioinformatics",
    "математическое моделирование", "искусственный интеллект", "большие данные"
]

AUTHORS = [
    "John Smith", "Maria Garcia", "Wei Chen", "Anna Kuznetsova", 
    "Ivan Petrov", "Hiroshi Tanaka", "Emma Wilson", "Mohammed Ali",
    "Сергей Иванов", "Елена Смирнова", "Александр Попов"
]

papers = []
for i in range(1, 100001):
    source = random.choice(SOURCES)
    topic = random.choice(TOPICS)
    year = random.randint(2019, 2024)
    
    paper = {
        "id": f"RSH-{source[:4].upper()}-{year}-{i:08d}",
        "title": f"{topic.title()}: A Comprehensive Study on Advanced Methods (Paper {i})",
        "title_ru": f"{topic.title()}: Комплексное исследование современных методов",
        "abstract": f"This paper explores {topic} in detail. We present novel approaches and evaluate them on standard benchmarks. Results show significant improvements over existing methods.",
        "source_type": source,
        "source_url": f"https://{source}.example.com/paper/{i}",
        "publication_year": year,
        "keywords": [topic, "research", "science"],
        "authors": [{"id": f"A{i}", "full_name": random.choice(AUTHORS), "affiliations": ["University"]}],
        "citation_count": random.randint(0, 500),
        "language": random.choice(["en", "ru"]),
        "has_pdf": random.choice([True, False])
    }
    papers.append(paper)

# Save to file
with open("backend/app/mock_papers_large.json", "w") as f:
    json.dump(papers, f)

print(f"Generated {len(papers):,} mock papers")
PYEOF
```

---

## Option 2: Deploy 24/7 Crawler to Google Cloud (RECOMMENDED)

### Step 1: Deploy the Continuous Crawler Job

```bash
cd /Users/mark/russian-science-hub

# Make sure you're logged in
gcloud auth login
gcloud config set project znayka-fresh-1771794343

# Deploy the crawler container
gcloud builds submit --tag gcr.io/znayka-fresh-1771794343/znayka-crawler:latest -f Dockerfile.crawler

# Create Cloud Run Job (runs continuously)
gcloud run jobs create znayka-crawler-24-7 \
  --image gcr.io/znayka-fresh-1771794343/znayka-crawler:latest \
  --max-retries 10 \
  --task-timeout 24h \
  --memory 4Gi \
  --cpu 4 \
  --set-env-vars="API_URL=https://znayka-674193695957.europe-north1.run.app,CRAWLER_MODE=continuous"

# Start it NOW
gcloud run jobs execute znayka-crawler-24-7

# Check logs
gcloud logging tail "resource.type=cloud_run_job" --format="value(textPayload)"
```

### Step 2: Set Up Scheduler (Auto-Restart Every Hour)

```bash
# Create scheduler to ensure crawler keeps running
gcloud scheduler jobs create http znayka-crawler-restart \
  --location=europe-north1 \
  --schedule="0 * * * *" \
  --uri="https://europe-north1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/znayka-fresh-1771794343/jobs/znayka-crawler-24-7:run" \
  --http-method=POST \
  --oauth-service-account-email=znayka-fresh-1771794343@appspot.gserviceaccount.com
```

### Step 3: Monitor 24/7 Crawler

```bash
# View crawler logs in real-time
gcloud logging tail "resource.labels.job_name=znayka-crawler-24-7"

# Check job status
gcloud run jobs describe znayka-crawler-24-7

# Stop crawler
gcloud run jobs delete znayka-crawler-24-7 --quiet
```

---

## Current Example Articles (From API)

Here's what you can actually search right now:

### Article 1: ArXiv Paper
```json
{
  "id": "RSH-ARX-2024-00000001",
  "title": "Deep Learning Approaches for Natural Language Processing",
  "title_ru": "Методы глубокого обучения для обработки естественного языка",
  "abstract": "This paper explores various deep learning architectures for NLP tasks.",
  "source_type": "arxiv",
  "source_url": "https://arxiv.org/abs/2401.001",
  "publication_year": 2024,
  "keywords": ["deep learning", "NLP", "transformers"],
  "authors": [{"full_name": "John Smith", "affiliations": ["MIT"]}],
  "citation_count": 45,
  "language": "en"
}
```

**Search it:** https://znayka-frontend.vercel.app/search?q=deep+learning

### Article 2: CyberLeninka (Russian)
```json
{
  "id": "RSH-CL-2024-00000002",
  "title": "Neural Networks in Medical Diagnosis",
  "title_ru": "Нейронные сети в медицинской диагностике",
  "abstract": "Application of neural networks for diagnostic imaging analysis.",
  "source_type": "cyberleninka",
  "source_url": "https://cyberleninka.ru/article/n/123",
  "publication_year": 2024,
  "keywords": ["neural networks", "medicine", "AI"],
  "authors": [{"full_name": "Иван Петров", "affiliations": ["МГУ"]}],
  "citation_count_rsci": 45,
  "language": "ru"
}
```

**Search it:** https://znayka-frontend.vercel.app/search?q=neural

---

## Speed Optimization

### Current Speed vs Optimized

| Metric | Current | Optimized |
|--------|---------|-----------|
| Papers per crawl | 100-1000 | 5000-10000 |
| Parallel crawls | 9 | 27 (3× workers) |
| Delay between queries | 15s | 1s |
| Expected papers/day | 100,000 | 1,000,000 |

### Fast Crawler Config

```python
# In continuous_crawler.py, update these:

CRAWL_CONFIG = {
    "papers_per_query": 5000,        # Was: 1000
    "concurrent_sources": 9,          # Already max
    "concurrent_queries": 3,          # Run 3 queries in parallel
    "delay_between_batches": 1,       # Was: 5s
    "check_interval": 5,              # Was: 15s
}

QUERIES = [
    # High-priority (run every round)
    "machine learning", "artificial intelligence", "deep learning",
    
    # Medium-priority (run every 2nd round)
    "neural networks", "computer vision", "NLP",
    
    # Run continuously without stopping
]
```

---

## Quick Start: Run 24/7 NOW

### Option A: Deploy to Cloud (True 24/7)

```bash
./deploy-continuous-crawler.sh
```

This deploys to Google Cloud and runs FOREVER, even if you turn off your computer.

### Option B: Run on Your Machine (Stops when you close laptop)

```bash
python3 backend/app/continuous_crawler.py --limit 5000
```

This runs on YOUR machine and stops when you:
- Close terminal
- Put laptop to sleep  
- Turn off computer

---

## Summary

| What You Want | How To Do It | Stops When? |
|---------------|--------------|-------------|
| Run on my machine | `python3 continuous_crawler.py` | You close terminal |
| Run 24/7 in cloud | `./deploy-continuous-crawler.sh` | Never (auto-restarts) |
| Faster crawling | Edit config above | - |
| More papers for search | Deploy PostgreSQL + real crawlers | - |

**For REAL 24/7:** You MUST deploy to Google Cloud. Running locally only works while your computer is on.

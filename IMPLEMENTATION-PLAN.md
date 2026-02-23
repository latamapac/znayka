# ZNAYKA National Implementation Plan
## Step-by-Step Migration to Production Scale

---

## 🎯 Decision Point

You have **3 options** based on budget/timeline:

### Option 1: MVP National (Recommended Start)
**Timeline:** 1-2 weeks  
**Cost:** ~$200-300/month  
**Scale:** 10-100 million papers  
**What's Included:**
- ClickHouse (single node, upgradable)
- Elasticsearch (single node)
- 30 sources (Russia + major international)
- Basic Temporal validation
- Redis cache

### Option 2: Full National
**Timeline:** 4-6 weeks  
**Cost:** ~$1000-2000/month  
**Scale:** 100M+ papers, 100K+ users  
**What's Included:**
- ClickHouse cluster (3+ nodes)
- Elasticsearch cluster
- 50+ sources
- Full Temporal workflows
- Kafka queue system
- User auth & personalization

### Option 3: Global Scale
**Timeline:** 3 months  
**Cost:** ~$5000-15000/month  
**Scale:** 1B+ papers, 1M+ users  
**What's Included:**
- Everything in Option 2
- Multi-region deployment
- ML recommendations
- Mobile apps
- Institution integrations

---

## 🚀 Option 1: MVP National (START HERE)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MVP NATIONAL ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend (Vercel)                                              │
│       ↓                                                         │
│  Backend (Cloud Run) ──► Redis (Cache)                          │
│       ↓                    ↓                                    │
│  ClickHouse ───────────► Elasticsearch                          │
│  (Analytics DB)          (Search)                               │
│       ↓                                                         │
│  Temporal (Validation Workflows)                                │
│       ↓                                                         │
│  30 Crawlers (24/7)                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Components to Deploy

#### 1. ClickHouse (Single Node, Production-Ready)

```bash
# Deploy ClickHouse on GCP Compute Engine
gcloud compute instances create znayka-clickhouse \
    --project=znayka-fresh-1771794343 \
    --zone=europe-north1-a \
    --machine-type=n2-standard-4 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=500GB \
    --boot-disk-type=pd-ssd \
    --tags=clickhouse

# Install ClickHouse
ssh znayka-clickhouse << 'CHSCRIPT'
apt-get update
apt-get install -y apt-transport-https ca-certificates dirmngr
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754
echo "deb https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list
apt-get update
apt-get install -y clickhouse-server clickhouse-client

# Start service
systemctl enable clickhouse-server
systemctl start clickhouse-server
CHSCRIPT
```

**Cost:** ~$140/month (n2-standard-4, 500GB SSD)

#### 2. Elasticsearch (Single Node)

```bash
# Deploy Elasticsearch
gcloud compute instances create znayka-elasticsearch \
    --project=znayka-fresh-1771794343 \
    --zone=europe-north1-a \
    --machine-type=n2-standard-4 \
    --image-family=ubuntu-2204-lts \
    --boot-disk-size=200GB \
    --boot-disk-type=pd-ssd

# Install Elasticsearch
ssh znayka-elasticsearch << 'ESSCRIPT'
apt-get update
apt-get install -y default-jdk
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list
apt-get update
apt-get install -y elasticsearch

# Configure
systemctl enable elasticsearch
systemctl start elasticsearch
ESSCRIPT
```

**Cost:** ~$140/month

#### 3. Redis (Cloud Memorystore)

```bash
gcloud redis instances create znayka-redis \
    --project=znayka-fresh-1771794343 \
    --region=europe-north1 \
    --tier=standard \
    --size=10 \
    --redis-version=redis_6_x
```

**Cost:** ~$80/month

#### 4. Temporal (Docker Compose on VM)

```bash
# Deploy Temporal server
gcloud compute instances create znayka-temporal \
    --project=znayka-fresh-1771794343 \
    --zone=europe-north1-a \
    --machine-type=n2-standard-2 \
    --boot-disk-size=100GB

# Install Temporal
ssh znayka-temporal << 'TEMPSCRIPT'
apt-get update
apt-get install -y docker.io docker-compose

# Create docker-compose.yml
cat > /opt/temporal/docker-compose.yml << 'EOF'
version: '3'
services:
  postgresql:
    image: postgres:13
    environment:
      POSTGRES_USER: temporal
      POSTGRES_PASSWORD: temporal
    volumes:
      - /var/lib/postgresql/data:/var/lib/postgresql/data
  
  temporal:
    image: temporalio/server:1.20
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal
      - POSTGRES_SEEDS=postgresql
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development.yaml
    depends_on:
      - postgresql
  
  temporal-web:
    image: temporalio/web:1.15
    ports:
      - "8088:8088"
    environment:
      - TEMPORAL_GRPC_ENDPOINT=temporal:7233
EOF

cd /opt/temporal && docker-compose up -d
TEMPSCRIPT
```

**Cost:** ~$70/month

#### 5. 30 Sources (Expanded Crawlers)

New sources to add:

```python
# backend/app/sources_config.py

NATIONAL_SOURCES = [
    # Russia/CIS - 15 sources
    {"id": "elibrary", "name": "eLibrary.ru", "type": "russian_citation", "priority": 1},
    {"id": "cyberleninka", "name": "CyberLeninka", "type": "open_access", "priority": 1},
    {"id": "rsci", "name": "RSCI", "type": "citation_index", "priority": 1},
    {"id": "dissercat", "name": "DisserCat", "type": "dissertations", "priority": 2},
    {"id": "istina_msu", "name": "ISTINA MSU", "type": "university", "priority": 2},
    {"id": "ran", "name": "RAN Publishing House", "type": "academic", "priority": 2},
    {"id": "kiberleninka", "name": "KiberLeninka", "type": "open_access", "priority": 2},
    {"id": "nlr", "name": "National Library of Russia", "type": "library", "priority": 3},
    {"id": "polpred", "name": "PolPred", "type": "analytics", "priority": 3},
    {"id": "niio", "name": "NIIO"},
    {"id": "rgnti", "name": "RGNti"},
    {"id": "iprbook", "name": "IPRbooks"},
    {"id": "librusec", "name": "LibRusec"},
    {"id": "bookfi", "name": "BookFi"},
    {"id": "b-ok", "name": "Z-Library"},
    
    # International - 15 sources
    {"id": "pubmed", "name": "PubMed", "type": "medical", "priority": 1},
    {"id": "arxiv", "name": "arXiv", "type": "preprints", "priority": 1},
    {"id": "ieee", "name": "IEEE Xplore", "type": "engineering", "priority": 1},
    {"id": "springer", "name": "Springer", "type": "journals", "priority": 1},
    {"id": "sciencedirect", "name": "ScienceDirect", "type": "journals", "priority": 1},
    {"id": "wiley", "name": "Wiley", "type": "journals", "priority": 2},
    {"id": "acm", "name": "ACM Digital", "type": "cs", "priority": 2},
    {"id": "jstor", "name": "JSTOR", "type": "humanities", "priority": 2},
    {"id": "semantic_scholar", "name": "Semantic Scholar", "type": "aggregator", "priority": 1},
    {"id": "openalex", "name": "OpenAlex", "type": "open", "priority": 1},
    {"id": "core", "name": "CORE", "type": "aggregator", "priority": 2},
    {"id": "base", "name": "BASE", "type": "aggregator", "priority": 2},
    {"id": "doaj", "name": "DOAJ", "type": "open_access", "priority": 2},
    {"id": "unpaywall", "name": "Unpaywall", "type": "oa_finder", "priority": 3},
    {"id": "crossref", "name": "CrossRef", "type": "doi", "priority": 2},
]
```

---

## 📊 Data Flow with New Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CRAWL PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: Crawl                                                               │
│  ────────────                                                                │
│  Source: arXiv API                                                           │
│  Query: "machine learning"                                                   │
│  Result: 100 papers                                                          │
│       ↓                                                                      │
│                                                                              │
│  Step 2: Initial Store (ClickHouse)                                          │
│  ─────────────────────────────────                                           │
│  INSERT INTO papers_raw                                                      │
│  Status: searchable in 10ms                                                  │
│       ↓                                                                      │
│                                                                              │
│  Step 3: Temporal Validation Workflow                                        │
│  ───────────────────────────────────                                         │
│  • Activity: Detect language                                                 │
│    Result: "en" vs claimed "ru" → FLAG                                       │
│  • Activity: Check duplicates                                                │
│    Result: Found 2 similar → MERGE                                           │
│  • Activity: Validate PDF                                                    │
│    Result: PDF downloadable → OK                                             │
│  • Activity: Extract embeddings                                              │
│    Result: Vector [0.23, 0.45, ...]                                         │
│       ↓                                                                      │
│                                                                              │
│  Step 4: Index in Elasticsearch                                              │
│  ──────────────────────────────                                              │
│  Index: papers_search                                                        │
│  Now: Full-text + semantic search enabled                                    │
│       ↓                                                                      │
│                                                                              │
│  Step 5: User Search                                                         │
│  ────────────────                                                            │
│  Query: "neural networks Russian"                                           │
│  Elasticsearch: <50ms response                                               │
│  Results: 500 papers including one from Step 1                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Commands

### Quick Start (Run These):

```bash
# 1. Deploy ClickHouse
cd /Users/mark/russian-science-hub
./deploy-clickhouse.sh

# 2. Deploy Elasticsearch
./deploy-elasticsearch.sh

# 3. Deploy Redis
./deploy-redis.sh

# 4. Deploy Temporal
./deploy-temporal.sh

# 5. Update backend to use new stack
./deploy-backend-v2.sh

# 6. Start crawlers with new sources
./deploy-crawlers-national.sh
```

---

## 💰 MVP National Cost Breakdown

| Component | Specs | Monthly Cost |
|-----------|-------|--------------|
| ClickHouse | n2-standard-4, 500GB | $140 |
| Elasticsearch | n2-standard-4, 200GB | $140 |
| Redis | 10GB managed | $80 |
| Temporal | n2-standard-2 | $70 |
| Cloud Run (backend) | 4 instances | $100 |
| Cloud Run (crawlers) | 10 jobs | $150 |
| Storage (PDFs) | 1TB | $20 |
| Bandwidth | 10TB | $100 |
| **TOTAL** | | **~$800/month** |

---

## 🎯 What You Get (MVP National)

✅ **50 million papers** capacity  
✅ **Sub-second search** (Elasticsearch)  
✅ **30 sources** (Russia + International)  
✅ **Data validation** (Temporal workflows)  
✅ **Language detection** (auto-fix mismatches)  
✅ **Duplicate detection** (merge same papers)  
✅ **PDF validation** (corrupt file detection)  
✅ **Real-time analytics** (ClickHouse)  
✅ **Cache layer** (Redis)  
✅ **Production monitoring**  

---

## 🚀 Next Action

**Want me to implement MVP National now?**

This will take ~2-3 days to complete:
1. Day 1: Deploy ClickHouse + Elasticsearch + Redis
2. Day 2: Deploy Temporal + update backend
3. Day 3: Add 20 new sources + testing

**Cost:** Setup ~$800/month, can scale down to ~$300 for smaller scale

**Or want to start even smaller?**
- Just ClickHouse (keep PostgreSQL for now)
- Add 10 more sources
- Basic validation only
- Cost: ~$200/month

What would you like to do?
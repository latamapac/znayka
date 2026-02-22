# Deploy ZNAYKA to Contabo VPS (Recommended)

## Why Contabo?
- **VPS M**: 8GB RAM, 4 vCPU = **$10/month**
- PyTorch fits easily (needs 3-4GB)
- Full control (Docker, systemd, etc.)
- Better than Railway for ML workloads

## Quick Deploy

### 1. Buy VPS M on Contabo
https://contabo.com/en/vps/
- Choose **VPS M** (8GB RAM)
- Location: US or EU
- OS: Ubuntu 22.04

### 2. SSH into server
```bash
ssh root@YOUR_CONTABO_IP
```

### 3. Install Docker
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 4. Clone and deploy
```bash
git clone https://github.com/latamapac/znayka.git
cd znayka

# Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://znayka:znayka@postgres:5432/znayka
USE_SQLITE=false
SEED_DATABASE=true
EOF

# Start everything
docker-compose up -d
```

### 5. Done!
- API: http://YOUR_CONTABO_IP:8080
- API Docs: http://YOUR_CONTABO_IP:8080/docs

## Docker Compose (Production)

```yaml
version: "3.8"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: znayka
      POSTGRES_PASSWORD: znayka
      POSTGRES_DB: znayka
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://znayka:znayka@postgres:5432/znayka
      - USE_SQLITE=false
    ports:
      - "8080:8000"
    depends_on:
      - postgres
    restart: always
    deploy:
      resources:
        limits:
          memory: 6G

volumes:
  postgres_data:
```

## Railway Hobby Alternative

If staying on Railway Hobby (2GB):

```bash
# Use CPU-only PyTorch (smaller)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

But **Contabo VPS M (8GB)** is more reliable for ML.

## Run Crawler

```bash
# SSH to Contabo
docker exec -it znayka-backend-1 bash

# Run crawler
python -m crawlers.orchestrator --query "machine learning" --limit 100
```

## Total Cost
- Contabo VPS M: **$10/month**
- Domain (optional): **$10/year**
- **Total: ~$11/month**

Cheaper than Render paid ($25/mo) and more RAM!

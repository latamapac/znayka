# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 50GB disk space

## Quick Start with Docker Compose

1. Clone the repository:
```bash
git clone <repository-url>
cd russian-science-hub
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start all services:
```bash
make setup
# or manually:
docker-compose up --build -d
```

4. Run database migrations:
```bash
make migrate
```

5. Access the application:
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Production Deployment

### 1. Server Requirements

- Ubuntu 22.04 LTS or similar
- 4+ CPU cores
- 16GB+ RAM
- 200GB+ SSD storage

### 2. Environment Configuration

Create a production `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:strong_password@postgres:5432/russia_science_hub
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=russia_science_hub

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI (optional, for embeddings)
OPENAI_API_KEY=sk-...

# Security
SECRET_KEY=your-super-secret-production-key

# Storage
PAPERS_STORAGE_PATH=/data/papers
```

### 3. SSL/TLS with Let's Encrypt

Use nginx-proxy with acme-companion:

```yaml
# Add to docker-compose.yml
services:
  nginx-proxy:
    image: nginxproxy/nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/tmp/docker.sock:ro
      - certs:/etc/nginx/certs
      - vhost:/etc/nginx/vhost.d
      - html:/usr/share/nginx/html

  acme-companion:
    image: nginxproxy/acme-companion
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - certs:/etc/nginx/certs
      - acme:/etc/acme.sh
    environment:
      - DEFAULT_EMAIL=your-email@example.com
```

Add to backend and frontend services:
```yaml
environment:
  - VIRTUAL_HOST=api.yourdomain.com
  - LETSENCRYPT_HOST=api.yourdomain.com
```

### 4. Database Backup

Create backup script:

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker-compose exec -T postgres pg_dump -U postgres russia_science_hub > $BACKUP_DIR/db_$DATE.sql

# Backup papers
tar -czf $BACKUP_DIR/papers_$DATE.tar.gz /data/papers

# Keep only last 7 backups
ls -t $BACKUP_DIR/db_*.sql | tail -n +8 | xargs rm -f
ls -t $BACKUP_DIR/papers_*.tar.gz | tail -n +8 | xargs rm -f
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### 5. Monitoring

Install Prometheus and Grafana for monitoring:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
```

## Cloud Deployment

### AWS Deployment

1. Create EC2 instance (t3.large or larger)
2. Install Docker and Docker Compose
3. Clone repository and configure
4. Use Application Load Balancer for SSL termination
5. Configure RDS for PostgreSQL (optional)
6. Configure ElastiCache for Redis (optional)

### Yandex Cloud Deployment

1. Create VM in Yandex Cloud
2. Use Yandex Managed Service for PostgreSQL
3. Use Yandex Object Storage for PDF files
4. Configure security groups

```bash
# Install YC CLI
curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash

# Authenticate
yc init

# Create VM
yc compute instance create \
  --name rsh-server \
  --zone ru-central1-a \
  --cores 4 \
  --memory 8G \
  --image-folder-id standard-images \
  --image-family ubuntu-2204-lts \
  --ssh-key ~/.ssh/id_rsa.pub
```

## Scaling

### Horizontal Scaling

Use Docker Swarm or Kubernetes:

```bash
# Initialize Swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml russian-science-hub

# Scale services
docker service scale russian-science-hub_backend=3
```

### Database Scaling

1. Use read replicas for search queries
2. Partition papers table by year
3. Use connection pooling (PgBouncer)

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running
   - Verify DATABASE_URL format
   - Check firewall rules

2. **Embeddings not generating**
   - Verify OpenAI API key
   - Check GPU/CPU resources
   - Review Celery worker logs

3. **High memory usage**
   - Increase swap space
   - Reduce embedding batch size
   - Use quantized embedding models

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# View Celery worker logs
docker-compose logs -f celery_worker
```

## Security Checklist

- [ ] Change default passwords
- [ ] Enable SSL/TLS
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable database encryption at rest
- [ ] Use secrets management for API keys
- [ ] Regular security updates
- [ ] Monitor for suspicious activity

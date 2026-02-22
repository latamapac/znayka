.PHONY: help setup start stop restart logs migrate test clean

help: ## Show this help message
	@echo "Russian Science Hub - Available Commands"
	@echo "========================================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial setup of the project
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

start: ## Start all services
	@docker-compose up -d

stop: ## Stop all services
	@docker-compose down

restart: ## Restart all services
	@docker-compose restart

logs: ## View logs from all services
	@docker-compose logs -f

migrate: ## Run database migrations
	@docker-compose exec backend alembic upgrade head

makemigrations: ## Create new database migration
	@docker-compose exec backend alembic revision --autogenerate -m "$(m)"

backend-shell: ## Open a shell in the backend container
	@docker-compose exec backend bash

crawl: ## Run crawler (usage: make crawl q="machine learning" source=cyberleninka limit=50)
	@docker-compose exec backend python -m crawlers.orchestrator \
		--query "$(q)" \
		--source $(source) \
		--limit $(or $(limit),20)

test: ## Run tests
	@docker-compose exec backend pytest -v

lint: ## Run linting
	@docker-compose exec backend black .
	@docker-compose exec backend isort .
	@docker-compose exec backend flake8 .

frontend-install: ## Install frontend dependencies
	@docker-compose exec frontend npm install

frontend-build: ## Build frontend for production
	@docker-compose exec frontend npm run build

clean: ## Clean up containers and volumes
	@docker-compose down -v
	@docker system prune -f

backup-db: ## Backup PostgreSQL database
	@mkdir -p backups
	@docker-compose exec postgres pg_dump -U postgres russia_science_hub > backups/backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore PostgreSQL database (usage: make restore-db file=backups/backup_xxx.sql)
	@docker-compose exec -T postgres psql -U postgres russia_science_hub < $(file)

stats: ## Show database statistics
	@docker-compose exec backend python -c "
import asyncio
from app.db.base import AsyncSessionLocal
from app.services.indexing_service import IndexingService

async def show_stats():
    async with AsyncSessionLocal() as db:
        service = IndexingService(db)
        stats = await service.get_index_stats()
        for key, value in stats.items():
            print(f'{key}: {value}')

asyncio.run(show_stats())
"

update-embeddings: ## Update embeddings for papers without them
	@docker-compose exec backend python -c "
import asyncio
from crawlers.orchestrator import CrawlerOrchestrator

async def update():
    orchestrator = CrawlerOrchestrator()
    count = await orchestrator.update_embeddings()
    print(f'Updated embeddings for {count} papers')

asyncio.run(update())
"

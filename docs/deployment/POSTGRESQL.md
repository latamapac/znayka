# PostgreSQL + pgvector Setup Guide

## Установка PostgreSQL

### Mac (Homebrew)

```bash
# Установка PostgreSQL 15
brew install postgresql@15

# Добавление в PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Запуск сервиса
brew services start postgresql@15
```

### Ubuntu/Debian

```bash
# Установка
sudo apt update
sudo apt install postgresql-15 postgresql-contrib

# Запуск
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Установка pgvector

### Mac

```bash
brew install pgvector
```

### Ubuntu

```bash
# Для PostgreSQL 15
sudo apt install postgresql-15-pgvector

# Или компиляция из исходников
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

## Настройка базы данных

```bash
# Создание базы
psql -U postgres -c "CREATE DATABASE russia_science_hub;"

# Подключение и создание расширений
psql -U postgres -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Проверка
psql -U postgres -d russia_science_hub -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

## Конфигурация backend

### 1. Обновить .env

```bash
cd backend

# Удалить USE_SQLITE или установить в false
unset USE_SQLITE

# Создать .env для PostgreSQL
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/russia_science_hub
SECRET_KEY=your-secret-key-min-32-characters-long
API_V1_PREFIX=/api/v1
PROJECT_NAME="Russian Science Hub"
PROJECT_VERSION=0.1.0
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
EMBEDDING_DIMENSION=384
PORT=8000
EOF
```

### 2. Установить asyncpg

```bash
pip install asyncpg
```

### 3. Запуск с PostgreSQL

```bash
# Миграции
unset USE_SQLITE  # Важно!
cd backend
alembic upgrade head

# Или создать таблицы автоматически
python3 -c "
import asyncio
import os
os.environ.pop('USE_SQLITE', None)  # Удалить SQLite переменную
from app.db.base import init_db
asyncio.run(init_db())
print('PostgreSQL tables created!')
"

# Запуск
uvicorn app.main:app --reload --port 8000
```

## Проверка работы

```bash
# Проверка подключения
curl http://localhost:8000/health

# Проверка pgvector (semantic search должен работать)
curl -X POST http://localhost:8000/api/v1/papers/semantic-search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 5}'
```

## Docker (альтернатива)

```bash
# Запуск PostgreSQL + pgvector в Docker
docker run -d \
  --name rsh-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=russia_science_hub \
  -p 5432:5432 \
  ankane/pgvector:latest

# Проверка
docker exec rsh-postgres psql -U postgres -d russia_science_hub -c "CREATE EXTENSION vector;"
```

## Railway (Production)

```bash
# Добавить PostgreSQL в Railway
railway add --database postgres

# Переменные окружения автоматически добавятся
# DATABASE_URL=postgresql://...
```

## Различия SQLite vs PostgreSQL

| Функция | SQLite | PostgreSQL |
|---------|--------|------------|
| Текстовый поиск | ✅ | ✅ |
| Семантический поиск | ❌ | ✅ |
| Hybrid search | ❌ | ✅ |
| Похожие статьи | ❌ | ✅ |
| Масштабируемость | Ограничена | Высокая |
| Параллельные запросы | ❌ | ✅ |

## Оптимизация PostgreSQL

```sql
-- Индексы для быстрого поиска
CREATE INDEX idx_papers_title_trgm ON papers USING gin(title gin_trgm_ops);
CREATE INDEX idx_papers_year ON papers(publication_year);
CREATE INDEX idx_papers_source ON papers(source_type);

-- Проверка использования индексов
EXPLAIN ANALYZE SELECT * FROM papers WHERE title ILIKE '%machine%';
```

## Troubleshooting

### "pgvector extension not available"
```bash
# Переустановка pgvector
cd /tmp && rm -rf pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector && make && sudo make install
# Перезапуск PostgreSQL
brew services restart postgresql@15
```

### "connection refused"
```bash
# Проверка статуса
brew services list | grep postgresql

# Проверка порта
lsof -i :5432
```

### "permission denied"
```bash
# Создание пользователя
psql -U postgres -c "CREATE USER myuser WITH PASSWORD 'password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE russia_science_hub TO myuser;"
```

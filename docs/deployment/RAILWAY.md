# Deploy to Railway

Railway предоставляет простой способ деплоя приложения с автоскейлингом и managed PostgreSQL.

## Быстрый старт

### 1. Установка CLI (опционально)

```bash
npm install -g @railway/cli
railway login
```

### 2. Создание проекта

```bash
# Через CLI
cd russian-science-hub/backend
railway init

# Или через веб-интерфейс:
# 1. Перейди на https://railway.app
# 2. Нажми "New Project"
# 3. Выбери "Deploy from GitHub repo"
```

### 3. Добавление базы данных

```bash
# Через CLI
railway add --database postgres
railway add --database redis

# Или через Dashboard:
# New → Database → Add PostgreSQL
# New → Database → Add Redis
```

### 4. Настройка переменных окружения

В Railway Dashboard → Variables добавь:

```bash
# Database (Railway сам подставит значения при подключении Postgres)
DATABASE_URL=${{Postgres.DATABASE_URL}}
# Или вручную:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:port/railway

# Redis
REDIS_URL=${{Redis.REDIS_URL}}

# Security
SECRET_KEY=your-super-secret-key-min-32-chars-long

# OpenAI (опционально)
OPENAI_API_KEY=sk-...

# CORS
CORS_ORIGINS=https://your-frontend-url.up.railway.app,http://localhost:5173
```

### 5. Деплой Backend

```bash
cd backend
railway up
```

### 6. Деплой Frontend (отдельный сервис)

Создай новый сервис в том же проекте:

```bash
cd frontend
railway init --service frontend
railway up
```

Установи переменные:
```bash
VITE_API_URL=https://your-backend-url.up.railway.app/api/v1
```

## Монорепозиторий (все сервисы вместе)

### Вариант 1: Только Backend (с авто-скейлингом)

```bash
# Railway автоматически использует backend/Dockerfile
cd russian-science-hub
railway init
railway up
```

### Вариант 2: Nixpacks (без Docker)

Создай `nixpacks.toml` в корне:

```toml
[phases.build]
cmds = [
  "cd backend && pip install -r requirements.txt",
  "cd frontend && npm install && npm run build"
]

[phases.setup]
nixPkgs = ["python312", "nodejs_20"]

[start]
cmd = "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

## Миграции базы данных

После деплоя запусти миграции:

```bash
railway run --service backend "alembic upgrade head"

# Или через Dashboard → Shell:
# cd backend && alembic upgrade head
```

## Проверка работы

```bash
# Health check
curl https://your-app.up.railway.app/health

# API
curl https://your-app.up.railway.app/api/v1/papers/search?q=test
```

## Troubleshooting

### Ошибка: "Module not found"
```bash
# Пересобрать с чистого
railway up --clean
```

### Ошибка подключения к БД
```bash
# Проверь DATABASE_URL
railway variables

# Должно содержать postgresql+asyncpg://
```

### Рестарт сервиса
```bash
railway restart
```

### Логи
```bash
railway logs --follow
```

## Домен

Railway автоматически дает домен:
- `https://your-service-name.up.railway.app`

Кастомный домен:
1. Dashboard → Settings → Domains
2. Generate Domain (или добавь свой)

## Бесплатный лимит

- $5 credits в месяц (хватает для небольшого проекта)
- 512 MB RAM
- 1 GB хранилище
- 100 GB трафика

## Полезные команды

```bash
# Статус
railway status

# Переменные окружения
railway variables

# Shell в контейнере
railway shell

# Локальный запуск с переменными Railway
railway run

# Просмотр логов
railway logs

# Удаление сервиса
railway down
```

## Альтернатива: Docker Compose в Railway

Railway не поддерживает docker-compose напрямую, но можно:

1. Развернуть каждый сервис отдельно
2. Или использовать `railway.yml` для мультисервисного деплоя:

```yaml
services:
  backend:
    build:
      context: ./backend
    ports:
      - 8000
    env:
      - DATABASE_URL
      - REDIS_URL
  
  frontend:
    build:
      context: ./frontend
    ports:
      - 5173
```

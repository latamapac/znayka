# Quick Start Guide

## 🚀 Быстрый запуск (без Docker)

### Требования
- Python 3.10+
- Node.js 18+
- (опционально) PostgreSQL - если хотите полную функциональность

### 1. Запуск

```bash
cd /Users/mark/russian-science-hub
./start.sh
```

Или с другими портами (если 8000/5173 заняты):
```bash
./start.sh 8080 3000  # backend:8080, frontend:3000
./start.sh 9000 4000  # backend:9000, frontend:4000
```

Это автоматически:
- Установит Python зависимости
- Создаст SQLite базу данных
- Инициализирует таблицы
- Запустит Backend (порт 8000)
- Установит npm пакеты
- Запустит Frontend (порт 5173)

### 2. Откройте в браузере

```
http://localhost:5173
```

API документация: http://localhost:8000/docs

### 3. Остановка

Нажмите `Ctrl+C` в терминале

---

## 📦 Ручная установка

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-minimal.txt

# Создать .env файл
cat > .env << 'EOF'
USE_SQLITE=true
DATABASE_URL=sqlite+aiosqlite:///./russia_science_hub.db
SECRET_KEY=your-secret-key
EOF

# Запуск
python3 -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## ⚠️ Ограничения SQLite версии

| Функция | SQLite | PostgreSQL |
|---------|--------|------------|
| Текстовый поиск | ✅ | ✅ |
| Семантический поиск | ❌ | ✅ |
| Hybrid поиск | ❌ | ✅ |
| Похожие статьи | ❌ | ✅ |

Для полной функциональности используйте PostgreSQL с pgvector.

---

## 🐘 PostgreSQL (опционально)

```bash
# Mac
brew install postgresql@15
brew services start postgresql@15

# Создать базу
createdb russia_science_hub
psql -d russia_science_hub -c "CREATE EXTENSION IF NOT EXISTS vector;"

# В backend/.env:
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/russia_science_hub
```

---

## 🛠️ Устранение проблем

### "Module not found"
```bash
pip install имя_модуля
# или
pip install -r backend/requirements-minimal.txt
```

### "Port already in use"
```bash
# Вариант 1: Использовать другие порты
./start.sh 8080 3000

# Вариант 2: Найти и убить процесс
lsof -i :8000
kill -9 <PID>
```

### "Permission denied"
```bash
chmod +x start.sh
```

---

## 📁 Структура проекта

```
russian-science-hub/
├── start.sh              # Главный скрипт запуска
├── backend/              # FastAPI + SQLite/PostgreSQL
│   ├── app/
│   │   ├── main.py       # Entry point
│   │   ├── api/          # REST endpoints
│   │   ├── models/       # Database models
│   │   └── services/     # Business logic
│   └── requirements.txt
├── frontend/             # React + Vite
│   ├── src/
│   │   ├── pages/        # Page components
│   │   └── components/   # UI components
│   └── package.json
└── crawlers/             # Paper crawlers
    └── sources/          # 9 source implementations
```

---

## 🌐 Railway деплой

```bash
npm install -g @railway/cli
railway login
./scripts/deploy-railway.sh
```

Или вручную:
```bash
cd backend && railway up
cd frontend && railway up
```

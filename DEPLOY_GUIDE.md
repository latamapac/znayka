# 🚀 Деплой ZNAYKA на Railway

## Шаг 1: GitHub (в браузере)

1. Открой https://github.com/new
2. Repository name: `znayka`
3. НЕ добавляй README (уже есть)
4. Нажми "Create repository"

## Шаг 2: Push кода (в терминале)

```bash
cd /Users/mark/russian-science-hub

# Удалить старый remote если есть
git remote remove origin 2>/dev/null || true

# Добавить новый (ЗАМЕНИ USERNAME!)
git remote add origin https://github.com/YOUR_USERNAME/znayka.git

# Push
git branch -M main
git push -u origin main
```

Если просит пароль — используй GitHub Token:
- Settings → Developer settings → Personal access tokens → Generate new token

## Шаг 3: Railway (в браузере)

1. Открой https://railway.app
2. New Project → Deploy from GitHub repo
3. Выбери репозиторий `znayka`
4. Нажми "Deploy"

### Добавь PostgreSQL:
- Нажми "New" → Database → Add PostgreSQL

### Переменные окружения:
Перейди в Variables и добавь:
```
USE_SQLITE = false
SEED_DATABASE = true
```

### Перезапусти:
- Settings → Deploy → Deploy again

## Шаг 4: Проверка

URL будет вида: `https://znayka-production-xxxx.up.railway.app`

Проверь:
```bash
curl https://znayka-production-xxxx.up.railway.app/health
```

## После деплоя: запуск краулера

```bash
railway login
railway link
railway run "python -m crawlers.orchestrator --query 'machine learning' --limit 50"
```

---

## Проблемы?

- **Push не работает** → Используй GitHub Token вместо пароля
- **Railway не видит репо** → Проверь права доступа в GitHub App
- **Ошибка БД** → Проверь что DATABASE_URL создана автоматически

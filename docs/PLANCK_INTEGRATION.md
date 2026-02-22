# Planck Big Data Integration

Интеграция с Planck Analytics Platform для продвинутой аналитики научных публикаций.

## Возможности

### 📊 Big Data Analytics
- **Trend Analysis** - Анализ трендов публикаций по годам и областям
- **Citation Networks** - Сети цитирования с визуализацией
- **Author Collaboration** - Анализ коллабораций авторов
- **Topic Modeling** - Тематическое моделирование

### 📈 Superset Dashboards
- Интеграция с Apache Superset
- Визуализация статистики
- Кастомные дашборды
- Real-time обновления

### 📤 Data Export
- CSV, JSON, Parquet форматы
- Фильтрация по источникам и годам
- Экспорт для внешнего анализа

## Настройка

### 1. Переменные окружения

```bash
# backend/.env
PLANCK_URL=http://localhost:3001
PLANCK_API_KEY=your-api-key
```

### 2. API Endpoints

```
GET  /api/v1/analytics/trends              # Тренды исследований
GET  /api/v1/analytics/statistics/comprehensive  # Комплексная статистика
POST /api/v1/analytics/query/bigdata       # Big Data запросы
GET  /api/v1/analytics/citations/network/{id}    # Сеть цитирования
GET  /api/v1/analytics/export              # Экспорт данных
GET  /api/v1/analytics/dashboards/superset # Superset дашборды
GET  /api/v1/analytics/planck/status       # Статус подключения
```

### 3. Примеры использования

```bash
# Получить тренды по машинному обучению
curl "http://localhost:8000/api/v1/analytics/trends?field=machine+learning&year_from=2020"

# Запустить Big Data анализ
curl -X POST "http://localhost:8000/api/v1/analytics/query/bigdata" \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "trends",
    "params": {
      "field": "artificial intelligence",
      "year_from": 2020,
      "year_to": 2024
    }
  }'

# Получить сеть цитирования
curl "http://localhost:8000/api/v1/analytics/citations/network/RSH-ELIB-2024-00000001?depth=2"
```

## Структура модуля

```
backend/app/integrations/
├── __init__.py
└── planck_bigdata.py          # Клиент Planck

backend/app/api/endpoints/
└── analytics.py               # API endpoints
```

## Planck Module (из Planck Project)

```typescript
// modules/analytics/manifest.ts
export const analyticsManifest: ModuleManifest = {
  id: 'analytics',
  name: 'Analytics',
  description: 'Dashboards, reports, and big data analytics',
  routes: [
    { path: '/analytics/superset', label: 'Superset Dashboards' },
    { path: '/analytics/query', label: 'Visual Query Builder' },
    { path: '/analytics/reports', label: 'Reports' },
  ],
  permissions: [
    { action: 'execute', resource: 'queries', description: 'Run analytics queries' },
  ],
  collections: ['reports'],
};
```

## Архитектура

```
Russian Science Hub          Planck Platform
        │                          │
        ├─► API Request ───────────┤
        │                          ▼
        │                    [Superset]
        │                    [Analytics]
        │                    [BigQuery]
        │                          │
        └◄─ Response ◄─────────────┘
```

## Fallback Mode

Если Planck недоступен, система автоматически использует локальную статистику:

```python
# Planck client automatically falls back to local data
planck = get_planck_client()
stats = await planck.get_paper_statistics()
# Returns local stats if Planck is down
```

## Production Setup

### Railway + Planck

```bash
# Добавить переменные в Railway
trailway variables set PLANCK_URL=https://planck.your-domain.com
railway variables set PLANCK_API_KEY=your-secret-key
```

### Docker Compose

```yaml
services:
  rsh-backend:
    environment:
      - PLANCK_URL=http://planck:3001
      - PLANCK_API_KEY=${PLANCK_API_KEY}
  
  planck:
    image: planck/analytics:latest
    ports:
      - "3001:3001"
```

## Типы Big Data запросов

| Тип | Описание | Параметры |
|-----|----------|-----------|
| trends | Тренды публикаций | field, year_from, year_to |
| citations | Анализ цитирований | paper_id, depth |
| authors | Сети авторов | author_id, collaboration_depth |
| topics | Тематический анализ | keywords, method |

## Примеры дашбордов Superset

1. **Papers Overview** - Обзор публикаций
   - Papers by Year (line chart)
   - Papers by Source (pie chart)
   - Citation Trends (area chart)

2. **Research Trends** - Тренды исследований
   - Topic Modeling (word cloud)
   - Emerging Fields (bar chart)
   - Author Networks (graph)

3. **Citation Analysis** - Анализ цитирований
   - Citation Network (force-directed graph)
   - Impact Factor Trends
   - Most Cited Papers

## Troubleshooting

### "Planck not connected"
```bash
# Проверить URL
curl http://localhost:3001/health

# Проверить конфигурацию
cat backend/.env | grep PLANCK
```

### Big Data queries timeout
```python
# Увеличить таймаут в planck_bigdata.py
timeout=300.0  # 5 minutes
```

## Roadmap

- [ ] Real-time streaming analytics
- [ ] ML-based paper recommendations
- [ ] Automated trend detection
- [ ] Integration with Google Scholar citations
- [ ] Cross-reference with ORCID profiles

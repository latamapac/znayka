# Russian Science Hub API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API is open access. Future versions will include API key authentication.

## Endpoints

### Search Papers

```http
GET /papers/search?q={query}&limit={limit}&offset={offset}&search_type={type}
```

Search for papers using various search strategies.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | Yes | Search query |
| limit | int | No | Results per page (default: 20, max: 100) |
| offset | int | No | Pagination offset (default: 0) |
| search_type | string | No | "text", "semantic", or "hybrid" (default: "hybrid") |
| year_from | int | No | Filter by year (from) |
| year_to | int | No | Filter by year (to) |
| source | string | No | Filter by source |
| journal | string | No | Filter by journal |

**Response:**

```json
{
  "papers": [...],
  "total": 1000,
  "limit": 20,
  "offset": 0,
  "search_type": "hybrid"
}
```

### Semantic Search

```http
POST /papers/semantic-search
```

Perform semantic search using natural language.

**Request Body:**

```json
{
  "query": "нейронные сети для обработки текста",
  "limit": 20,
  "offset": 0,
  "filters": {
    "year_from": 2020,
    "year_to": 2024
  }
}
```

### Get Paper by ID

```http
GET /papers/{paper_id}
```

Retrieve a specific paper by its unique ID.

**Example:**

```http
GET /papers/RSH-ELIB-2024-00000001
```

### Get Similar Papers

```http
GET /papers/{paper_id}/similar?limit={limit}
```

Find papers similar to the specified paper using vector similarity.

### Get Index Statistics

```http
GET /papers/stats/index
```

Get statistics about the indexed papers.

**Response:**

```json
{
  "total_papers": 1000000,
  "by_source": {
    "elibrary": 500000,
    "cyberleninka": 300000
  },
  "by_year": {
    "2024": 50000,
    "2023": 100000
  },
  "with_full_text": 800000,
  "processing_coverage": 80.0
}
```

### Add Paper (Manual Entry)

```http
POST /papers/
```

Add a new paper to the database (manual entry).

**Request Body:**

```json
{
  "title": "Paper Title",
  "title_ru": "Название статьи",
  "abstract": "Abstract text...",
  "doi": "10.1234/example",
  "authors": [
    {"full_name": "John Doe"}
  ],
  "source_type": "manual",
  "publication_year": 2024,
  "journal": "Journal Name",
  "keywords": ["keyword1", "keyword2"]
}
```

## Paper Object

```json
{
  "id": "RSH-ELIB-2024-00000001",
  "title": "Paper Title",
  "title_ru": "Название статьи",
  "abstract": "Abstract text...",
  "abstract_ru": "Аннотация...",
  "doi": "10.1234/example",
  "arxiv_id": null,
  "source_type": "elibrary",
  "source_url": "https://elibrary.ru/...",
  "journal": "Journal Name",
  "journal_ru": "Название журнала",
  "publication_year": 2024,
  "keywords": ["keyword1", "keyword2"],
  "keywords_ru": ["ключевое слово 1"],
  "authors": [
    {
      "id": "RSH-MANL-2024-...",
      "full_name": "Author Name",
      "full_name_ru": null,
      "affiliations": ["University"],
      "orcid": "0000-0000-0000-0000"
    }
  ],
  "citation_count": 10,
  "citation_count_rsci": 5,
  "pdf_url": "https://...",
  "language": "ru",
  "crawled_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## Error Responses

The API uses standard HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource (e.g., paper already exists)
- `500 Internal Server Error` - Server error

**Error Response Format:**

```json
{
  "detail": "Error message"
}
```

## Rate Limiting

API requests are rate-limited to:
- 100 requests per minute per IP
- 1000 requests per hour per IP

## SDK Examples

### Python

```python
import requests

API_URL = "http://localhost:8000/api/v1"

# Search papers
response = requests.get(f"{API_URL}/papers/search", params={
    "q": "machine learning",
    "limit": 10,
    "search_type": "hybrid"
})
papers = response.json()["papers"]

# Get paper by ID
response = requests.get(f"{API_URL}/papers/RSH-ELIB-2024-00000001")
paper = response.json()
```

### JavaScript/TypeScript

```typescript
// Search papers
const response = await fetch('/api/v1/papers/search?q=machine+learning&limit=10');
const data = await response.json();
console.log(data.papers);

// Semantic search
const response = await fetch('/api/v1/papers/semantic-search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'нейронные сети',
    limit: 10
  })
});
```

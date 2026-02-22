FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create storage directory
RUN mkdir -p /app/storage/papers

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080
EXPOSE 8080

# Use shell form to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}

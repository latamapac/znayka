FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
# Try light requirements first (CPU-only torch), fallback to minimal
COPY backend/requirements*.txt ./
RUN pip install --no-cache-dir -r backend/requirements.txt || \
    pip install --no-cache-dir -r backend/requirements-light.txt || \
    pip install --no-cache-dir -r backend/requirements-minimal.txt

# Copy application code
COPY backend/ .

# Make start script executable
RUN chmod +x start-production.sh

# Create storage directory
RUN mkdir -p /app/storage/papers

EXPOSE 8000

CMD ["./start-production.sh"]

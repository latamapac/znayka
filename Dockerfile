FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

# Create storage
RUN mkdir -p /app/storage/papers

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting ZNAYKA on port $PORT..."\n\
cd /app\n\
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1 --log-level info\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8080

# Use the startup script
CMD ["/app/start.sh"]

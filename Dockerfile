# Multi-stage build for Russian Science Hub
FROM python:3.12-slim as backend

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .
COPY crawlers/ /app/crawlers/

# Create startup script
RUN echo '#!/bin/bash\ncd /app/backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}' > /app/start-backend.sh && \
    chmod +x /app/start-backend.sh

EXPOSE 8000

CMD ["/app/start-backend.sh"]

# Frontend stage
FROM node:20-alpine as frontend

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Nginx stage for serving frontend
FROM nginx:alpine as nginx

COPY --from=frontend /app/frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# syntax=docker/dockerfile:1

# Build the React UI first, then package it with the FastAPI service in one
# runnable image. This keeps the first Docker milestone simple: one
# `docker run` command serves both the UI and the API.
FROM node:20-alpine AS frontend-build

WORKDIR /src/web-react
COPY web-react/package.json web-react/package-lock.json ./
RUN npm ci
COPY web-react/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ERP_DB_PATH=/app/data/erp.db \
    ERP_DEMO_MODE=true \
    API_CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY --from=frontend-build /src/web-react/dist/ /usr/share/nginx/html/
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/entrypoint.sh /usr/local/bin/erp-entrypoint
RUN chmod +x /usr/local/bin/erp-entrypoint

EXPOSE 5174

ENTRYPOINT ["/usr/local/bin/erp-entrypoint"]

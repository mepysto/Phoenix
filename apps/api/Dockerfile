# syntax=docker/dockerfile:1
# Phoenix API. Build context: repository root.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first so code changes don't invalidate this layer
COPY apps/api/pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py && pip install . && rm -rf src

COPY apps/api/ ./
RUN useradd --system --uid 10001 phoenix && chown -R phoenix /app
USER phoenix

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Alembic is the only schema source: migrate, then serve (no --reload in production;
# docker-compose.dev.yml overrides the command for hot reload)
CMD ["sh", "-c", "python -m scripts.migrate && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]

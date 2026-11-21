FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev

COPY data/sources.yaml /app/data/sources.yaml
ENV DB_PATH=/app/data/prawdowid.sqlite \
    CORPUS_PATH=/app/data/corpus.sqlite \
    SOURCES_PATH=/app/data/sources.yaml \
    INCIDENTS_DIR=/app/data/incidents \
    SOURCE_STATUS_PATH=/app/data/source_status.yaml \
    WEB_DIST_PATH=/app/web/dist \
    PATH="/app/backend/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "prawdowid.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

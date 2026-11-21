# Build from backend/:  docker build -t prawdowid-api backend
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.10.11 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
COPY data/sources.yaml data/source_status.yaml ./data/
COPY data/incidents ./data/incidents

ENV DB_PATH=/app/data/prawdowid.sqlite \
    CORPUS_PATH=/app/data/corpus.sqlite \
    SOURCES_PATH=/app/data/sources.yaml \
    INCIDENTS_DIR=/app/data/incidents \
    SOURCE_STATUS_PATH=/app/data/source_status.yaml \
    PATH="/app/.venv/bin:$PATH"

VOLUME ["/app/data"]
EXPOSE 8000
# Build the corpus once: docker run --env-file .env -v prawdowid-data:/app/data prawdowid-api python -m prawdowid.ingest build --allow-unverified --max-docs 15
CMD ["uvicorn", "prawdowid.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

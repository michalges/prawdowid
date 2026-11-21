# Build from backend/:  docker build -t prawdowid-api backend
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}

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
COPY docker-start.sh ./
RUN mkdir /app/state

ENV DB_PATH=/app/state/prawdowid.sqlite \
    CORPUS_PATH=/app/state/corpus.sqlite \
    SOURCES_PATH=/app/data/sources.yaml \
    INCIDENTS_DIR=/app/state/incidents \
    SOURCE_STATUS_PATH=/app/data/source_status.yaml \
    PATH="/app/.venv/bin:$PATH"

VOLUME ["/app/state"]
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/docker-start.sh"]
CMD ["uvicorn", "prawdowid.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

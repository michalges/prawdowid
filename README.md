# Prawdowid

Source-based verification of claims for Polish citizens (MSZ "PRAWDOWID" challenge). You send a claim, a link or a
screenshot. Prawdowid splits it into checkable claims and searches an auditable catalog of official sources. For each
claim it returns a plain-Polish result with verified quotes, or honestly says there isn't enough evidence.
It supports judgement. It is **not** an automatic "judge of truth".

Design: [`docs/CONCEPT.md`](docs/CONCEPT.md) · sources: [`docs/SOURCES.md`](docs/SOURCES.md) ·
open work: [`docs/TODO.md`](docs/TODO.md) · test results: [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md)

## Quick start (jury)

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY in .env.
docker compose up -d --build api
docker compose run --rm --build -p 127.0.0.1:8080:8080 web
```

Open `http://localhost:8080`. You can include the Discord bot locally with
`docker compose --profile discord up -d --build discord`.

Without Docker (Python 3.12 + [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run python -m prawdowid.ingest build --allow-unverified --max-docs 15
uv run prawdowid                  # serves on :8000
```

## Data & privacy

- Obvious personal data (e-mail, phone, PESEL, IBAN, card and ID numbers) is masked before the LLM call and before storage.
- Checks are deleted after `RETENTION_DAYS` (default 30). Sessions can be deleted via the API.
- Retrieval, embeddings and OCR run locally.
- The LLM runs through OpenRouter (a US intermediary) with provider data collection denied. For EU-only or self-hosted
  processing, use `LLM_PROVIDER=mistral` or `LLM_PROVIDER=ollama`.
- No API keys, personal data or organizer PDFs are committed. The PDFs contain personal names and stay local.

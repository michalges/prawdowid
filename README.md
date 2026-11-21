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

Try a check through the Compose web service (use port 8000 with the Python-only setup).

```bash
curl -s localhost:8080/v1/checks -H 'content-type: application/json' -d '{
  "channel": "web", "session_id": "demo-session-1",
  "input": {"type": "text", "text": "Rada Ministrów przyjęła 10 listopada 2026 projekt ustawy o systemie ETIAS."}
}' | python -m json.tool
```

`--allow-unverified` builds a local demo source collection from sources whose reuse terms haven't been formally verified yet
(see `docs/SOURCES.md` §3, §5).

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/checks` | Run a check: `text`, `url` or `image` input; the same call for every channel |
| `GET /v1/checks/{id}` | A stored result |
| `DELETE /v1/sessions/{id}` | Delete a session's data |
| `GET /v1/sources` | The auditable source catalog with document counts |
| `GET /health` | Components, model, source collection version, where data is processed |
| `GET /metrics`, `GET /v1/cases`, `GET /v1/export` | Admin (`Authorization: Bearer $ADMIN_TOKEN`) |

Every result separates **source material** (citations: title, publisher, date, link, verified quote) from **Prawdowid's
interpretation** (verdict, explanation, strength factors). Technical failures, rate limits and unclear questions come
back as statuses, never as verdicts.

## Development

```bash
cd backend
uv run ruff check . && uv run ruff format --check . && uv run pytest
uv run python eval/run_eval.py --output-dir /tmp/prawdowid-jury
uv run python eval/run_eval.py --cases path/to/jury_cases.jsonl
```

Pytest runs offline with mock providers. The [jury evaluation guide](backend/eval/README.md) describes the A–J suite, live prerequisites, and reports.

## Data & privacy

- Obvious personal data (e-mail, phone, PESEL, IBAN, card and ID numbers) is masked before the LLM call and before storage.
- Checks are deleted after `RETENTION_DAYS` (default 30). Sessions can be deleted via the API.
- Retrieval, embeddings and OCR run locally.
- The LLM runs through OpenRouter (a US intermediary) with provider data collection denied. For EU-only or self-hosted
  processing, use `LLM_PROVIDER=mistral` or `LLM_PROVIDER=ollama`.
- No API keys, personal data or organizer PDFs are committed. The PDFs contain personal names and stay local.

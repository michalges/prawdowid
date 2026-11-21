# TODO

What's missing or incomplete, kept current while working. Order follows CONCEPT §12. `[~]` = partially done.

## Track A: core

### A1. Skeleton
- [x] uv project, ruff, pytest, FastAPI app factory, `GET /health` (shows components + data-processing note)
- [x] API contract models (`schemas.py`), including the `mobile` channel, `case`, `extracted_text_pl`, `input_notices_pl`
- [x] LLM providers: `openrouter` (default `google/gemini-3.8-flash`; EU option `mistralai/mistral-large-4-0` is ~4× slower), JSON-schema output, `data_collection: deny`), `mistral`, `openai`, `anthropic` (SDK, optional extra), `ollama`, `mock` (offline, never decides), `failing`
- [ ] Live-test `anthropic`, `mistral` direct and `ollama` providers against real endpoints (only OpenRouter was tested live; the others are covered by mocked-HTTP tests)
- [ ] Re-check the OpenRouter price table (`providers/llm/__init__.py`) before reporting costs
- [ ] Choose the production embedding model (`sentence_transformers` provider exists; default is the offline `hashing` one); check its license (transferable to MSZ, Regulamin §4) and size, then rebuild the corpus
- [ ] Decide whether OpenRouter (US intermediary) is acceptable for the final demo: `OPENROUTER_EU_ROUTING=true` keeps processing in the EU but needs a Business plan (current key gets 403); alternatives are direct `mistral` (EU) or `ollama`

### A2. Corpus & ingest
- [x] `python -m prawdowid.ingest {check,build,stats}`: polite fetch (robots.txt, per-host delay, SSRF guard), trafilatura, chunking, FTS5 + vectors, `corpus_version`, idempotent rebuilds, excluded sources removed
- [x] Listing crawler skips menus/nav and prefers article-like links
- [~] Per-source verification (`docs/SOURCES.md` §5). Found so far (2026-11-21):
  - [x] Verified the seven hostname additions and documented exclusions in `docs/SOURCES.md`
  - `gov_ostrzezenia`, `msz_podrozujacy`: client-side rendered, so they're pointers only
  - `rcb_raport_dobowy`: the report is the page itself, so it's `page` mode
  - [ ] Review the legacy seed source licence flags before distributing a prebuilt corpus
- [ ] MSZ travel advisories: find the per-country advisory URLs (or an official feed) and ingest them. This is high value, since the organizer is MSZ.
- [ ] RCB daily report: keep daily snapshots (today each build replaces yesterday's text)
- [x] Ingest a static set of Demagog fact-check excerpts so the corpus has ≥ 2 source types without API keys
- [x] Add economics and EU policy sources from GUS, Eurostat and the European Commission
- [ ] Find crawlable, extractable official legal and open-data pages (see the skipped sources in `docs/SOURCES.md`)
- [ ] Get the organizer's incident DB (JSON/CSV) → `backend/data/incidents/` (loader ready)
- [ ] EUvsDisinfo export per the organizer's PDF → `backend/data/incidents/`
- [x] Reach the brief minimum (`ingest stats` prints it): ≥ 100 docs, ≥ 10 domains, ≥ 2 types
- [ ] Prebuilt `corpus.sqlite` as a release asset, so the jury doesn't need to crawl

### A3. Retrieval
- [x] Hybrid FTS5 BM25 + vectors + RRF, absolute relevance score, threshold gate, Polish prefix stemming + diacritics folding
- [x] Google Fact Check provider (+ recorded-response provider for tests), IFCN/EFCSN allowlist → tier B
- [ ] Record real Google Fact Check responses for offline tests (needs `GOOGLE_FACTCHECK_API_KEY`)
- [ ] Optional cross-encoder rerank
- [ ] Tune `RETRIEVAL_MIN_RELEVANCE` on the eval set

### A4. Verification
- [x] Claim extraction, judge (evidence-only, per-call random delimiters), deterministic citation verifier, re-judge after failed quotes, abstention gates, strength factors, archival notice, render
- [x] Incident matching + source-status notices (context only)
- [x] Prompts versioned in `prompts/*.md`
- [ ] Iterate on the prompts and thresholds against real eval runs
- [ ] `backend/data/source_status.yaml` has no verified entries yet (each needs an official legal reference)

### A5. Safety, privacy, ops
- [x] PII masking before the LLM and before storage (emails, phones, PESEL, IBAN/account numbers, cards, ID numbers)
- [x] PII: mask person names "when obvious" (CONCEPT §4 step 2)
- [x] Injection detection (input + sources), events, user notice
- [x] Check log, `GET /v1/checks/{id}`, `DELETE /v1/sessions/{id}`, retention purge on startup
- [x] Periodic retention purge in the API lifespan, including moderator cases and event logs
- [x] Rate limiting (session + client IP), SSRF guard, size limits, result cache, metrics, admin export
- [ ] SSRF: DNS rebinding window between our check and httpx's own resolution (pin the resolved IP)
- [ ] Rate limiter and cache are in-memory per process; move them to SQLite/Redis before running several workers
- [x] Moderator cases: grouping, counter, Discord webhook alert, "przekazano" only after confirmed delivery

## Track B: channels
- [x] Shared chat renderer + `ChannelAdapter` protocol (`channels/chat.py`)
- [ ] Web UI (React + Vite + TS + Tailwind) → built into `web/dist`, served by FastAPI at `/` (also needs the `/wynik/{id}` route used in chat links). Use `docs/DESIGN.md` + `docs/design/tokens.css`
- [ ] Discord embeds: take colours from `discord.*` from `docs/design/tokens.json`
- [ ] Web: replace the flag-tile wordmark in `Layout.tsx` and `public/favicon.svg` with the logo from `docs/design/logo/` (`docs/DESIGN.md` §9)
- [ ] Mobile: app icon and splash from `docs/design/logo/prawdowid-app-icon.svg`
- [ ] Discord: upload `docs/design/logo/discord/avatar-1024.png` and `banner-1360x480.png` in the Developer Portal (manual step)
- [x] Discord bot (`channels/discord_bot`): `/sprawdz` (text/link/image), `/usun_moje_dane`, DMs, @mentions, embeds with token colours, pseudonymous session ids
- [ ] Discord bot: live test with a real token; consistency harness run through the bot
- [ ] Demo chat adapter (`/demo-chat`)
- [ ] Mobile app (Expo)

## Track C: quality
- [x] `eval/run_eval.py` (all brief §6 metrics, `--cases` for the jury's set, `--base-url` for a deployment, manual-review sample) → `docs/TEST_RESULTS.md`
- [x] Expand `eval/cases.jsonl` to ≥ 30 cases with corpus-backed partly true, outdated and conflicting-source examples
- [ ] Expand scenario coverage to ≥ 3 cases per scenario A–J
- [ ] Fill in the manual citation review (`eval/manual_review.tsv`, 20 rows)

## Track D: delivery
- [x] Per-app deploys: `backend/Dockerfile` (with Tesseract `pol`) + `backend/.env.example`; `web/Dockerfile` + `web/.env.example`
- [x] Discord bot: its own Dockerfile + `.env.example` in `channels/discord_bot/`
- [ ] `README.md` with the jury quick start
- [ ] `docs/ARCHITECTURE.md` (incl. model licenses), `docs/RISKS.md`, `docs/COSTS.md`
- [ ] Public EU-hosted demo URL + Discord invite link
- [ ] Description ≤ 4,000 characters, PDF deck ≤ 12 slides, video ≤ 3 min

## Premium (after the gate passes; CONCEPT §9 order)
- [x] OCR screenshots (Tesseract `pol`, transcript shown, limits disclosed)
- [ ] pHash image matching
- [ ] Evidence chain view (web UI)
- [x] Information loop backend (cases, dedupe, counter, alerts)
- [x] CSV/JSON export
- [ ] DISARM/OpenCTI mapping note
- [ ] Multilingual retrieval check (EN sources, PL answer)
- [ ] Audio/video transcription (faster-whisper)
- [ ] Controlled archiving (default off)
- [ ] Self-hosted `ollama` mode documented and tested

## Open questions
- [ ] The organizer's full source list URL (brief §7) and incident DB: watch the Discord
- [x] Organizer PDFs contain personal names: removed from git history, kept locally, git-ignored

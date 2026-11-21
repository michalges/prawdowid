# CONCEPT.md: Prawdowid

> Hackathon project for the **MSZ "PRAWDOWID" challenge**: fast, easy, source-based verification of information.
> This file is the source of truth for every agent working on the repo. Read it fully before writing code.
> The authoritative brief is the organizer's PDF ("MSZ – Pełna treść zadania konkursowego") and the contest rules ("MSZ – Regulamin zadania konkursowego"). Keep them locally in `docs/`. **They are git-ignored and never committed, because they contain personal names.** Don't copy names from them into the repo. Sources: [`docs/SOURCES.md`](SOURCES.md) + `data/sources.yaml`. If this doc and the brief disagree, **the brief wins**: flag the conflict.

---

## 1. One-liner

A citizen sends a claim, a link or a screenshot **through a channel they already use** (web, Discord, or the mobile app, including straight from another app's **Share** menu or text-selection menu). Prawdowid splits it into checkable claims, searches a **clearly defined, auditable corpus** of official and fact-checking sources, and returns a plain-Polish result for each claim **with citations**. When the evidence isn't enough, it **honestly declines to give a verdict**.

It supports informed judgement. **It is not an automatic "judge of truth"** (brief §9).

## 2. What we are graded on (do not lose sight of this)

**Gate condition (brief §8):** without these, premium features score **zero**:
1. End-to-end operation with no manual intervention by the team.
2. No fabricated sources.
3. Correct abstention when evidence is missing.
4. Two working channels, or one channel + a demo adapter.

**Weights:** verification & evidence quality 30% · safety/accountability/transparency 20% · deployability & scalability 20% · usability & accessibility 15% · innovation & completeness 15%.

**Required metrics (brief §6), our targets:**

| Metric | Definition | Target |
|---|---|---|
| Verdict accuracy | macro-F1 over the supported classes | ≥ 0.75 |
| Citation coverage | % of factual statements backed by evidence | ≥ 95% |
| Citation correctness | the cited fragment actually supports the statement | ≥ 85% |
| Abstention | % of no-evidence cases correctly left without a verdict | ≥ 80% |
| Robustness | % of prompt-injection attempts repelled | ≥ 90% |
| Time | median input → answer, text/URL | ≤ 30 s |
| Cost | declared + measured cost of 100 tests | reported, lower is better |
| End-to-end | % of scenarios the jury runs without the team | 100% |
| Channel consistency | same verdict + evidence across channels | 100% |
| Info loop (if built) | correct case creation + dedupe | 100% |

**Non-goals:** a hard "truth score", AI-image detection as a verdict basis, verdicts based on domain/author/popularity, scraping paywalled or protected sources, Telegram/WeChat/niche platforms.

---

## 3. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend / verification core | **Python 3.12 + FastAPI**, uvicorn | Best ecosystem for retrieval and LLMs. |
| Python tooling | **uv** (deps, lockfile, running), **ruff** (lint + format), pytest | `uv run ruff check . && uv run ruff format --check . && uv run pytest` must pass. Commit `uv.lock`. Never use pip directly. |
| Storage | **SQLite** (one file): corpus, chunks, checks log, cases | Zero-ops, so the jury runs it with one command. |
| Lexical search | SQLite **FTS5** (BM25) | Polish inflection: index lowercased + simple stemming (see §6.4). |
| Vector search | Local multilingual embedding model (e.g. `BAAI/bge-m3` or `intfloat/multilingual-e5-base`) + in-memory numpy matrix, persisted to disk | The corpus is small (hundreds to thousands of chunks), so we don't need a vector DB. **Check license and size before choosing.** |
| Hybrid ranking | Reciprocal Rank Fusion (BM25 + vector) → optional cross-encoder rerank | Simple and strong. |
| LLM | Pluggable `LLMProvider`: **`openrouter`** (default: `google/gemini-3.8-flash` for the ≤ 30 s latency target; `mistralai/mistral-large-4-0` is the EU-vendor option; structured outputs; provider data collection denied), `mistral` (direct, EU), `openai`, `anthropic`, `ollama` (self-hosted, e.g. the Polish **Bielik** model) | One key gives access to many models for the hackathon. OpenRouter itself is a US intermediary, so that's disclosed in `/health` and the UI. The direct `mistral` and self-hosted `ollama` options remove the non-EEA hop (brief §3 premium). |
| URL fetching | `httpx` + `trafilatura` (main-text extraction) | Respect robots.txt and paywalls: **never bypass protections**. |
| Web UI | **React + Vite + TypeScript**, Tailwind | Responsive, accessible (WCAG AA contrast), served as static files by FastAPI. |
| Second channel | **Discord bot** (`discord.py`) | Allowed by the brief, the organizers run their channel there, and the jury can test it immediately. |
| Mobile app | **React Native (Expo, TypeScript, Expo Router)** + `expo-share-intent` (dev build / prebuild, not Expo Go) | Meets users where the content is: share a post, link, text or screenshot from Instagram, Facebook, X, the browser or the gallery straight into Prawdowid, without copy-pasting. One codebase for Android + iOS. |
| Demo adapter | `adapters/demo_chat`: a simulated messenger (HTTP + small chat UI) | A fallback for the gate condition, and a template for WhatsApp/Messenger later. |
| OCR (premium) | **Tesseract** with `pol` traineddata (local) | No external API, no data retention. Disclose its limits. |
| Packaging | **Docker Compose** (`api`, `discord-bot`); web is built into `api` | `docker compose up` + `.env` = running system. |
| Hosting (public demo) | An EU VPS / PaaS (e.g. Hetzner, OVH, Scaleway) | Transparent data location (brief §3, §5). |

Every external dependency (LLM, embeddings if remote, Discord) sits **behind an interface with a mock or offline implementation**, so the evaluation and tests run without keys and failures are shown as technical errors, never as verdicts (§7.4).

---

## 4. Architecture

```
            CHANNELS (no verification logic here)
┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐
│  Web UI      │  │  Discord bot     │  │  Demo chat adapter    │  │  Mobile app (RN/Expo)│
│  React/Vite  │  │  discord.py      │  │  (simulated messenger)│  │  in-app · Share menu │
└──────┬───────┘  └────────┬─────────┘  └───────────┬───────────┘  │  · text-select menu  │
       │                   │                        │              └──────────┬───────────┘
       │  ChannelMessage → POST /v1/checks  (same API, same core)             │
       ▼                   ▼                        ▼                         ▼
┌──────────────────────────── VERIFICATION CORE (FastAPI) ─────────────────────────┐
│ 0. Guard: auth/rate limit · input validation · size limits · request id          │
│ 1. Normalize: text | URL → fetch+extract | image → OCR (premium)                 │
│ 2. PII mask (emails, phones, PESEL, IBAN, names when obvious) → log only masked  │
│ 3. Claim extraction (LLM, JSON schema) → claims[] + "checkable?" + clarification │
│ 4. Retrieval per claim: hybrid BM25+vector → rerank → top-k evidence chunks      │
│    + incident-DB match (context only)  + source-status lookup (warning only)     │
│ 5. Judge per claim (LLM, evidence-only, injection-hardened, JSON schema)         │
│ 6. Citation verifier (deterministic): quotes must appear in the cited chunk      │
│ 7. Strength scoring (deterministic, explainable features)                        │
│ 8. Abstention policy: downgrade to "brak wystarczających dowodów" if gates fail  │
│ 9. Render plain-Polish answer · persist CheckRecord · metrics · (case creation)  │
└──────────────────────────────────────────────────────────────────────────────────┘
       │                         │                               │
┌──────▼──────┐   ┌──────────────▼─────────────┐   ┌─────────────▼─────────────┐
│ Corpus      │   │ Checks log / cases (SQLite)│   │ Provider adapters         │
│ SQLite+FTS5 │   │ retention + delete session │   │ LLM · embeddings · OCR    │
│ + vectors   │   └────────────────────────────┘   └───────────────────────────┘
└──────▲──────┘
       │ ingest pipeline (offline): sources.yaml → fetch → extract → chunk → embed
```

### Key design decisions
1. **Channels are thin.** They translate a platform message into `POST /v1/checks` and render the `CheckResult`. All logic lives in the core, which guarantees channel consistency (scenario G).
2. **The LLM only understands, compares and phrases.** Facts come from retrieved chunks. Every factual statement in the answer carries a `citation_id`, or it gets dropped.
3. **Citations are checked by code, not trusted.** The judge must return verbatim quotes. The verifier fuzzy-matches each quote against the cited chunk (normalized whitespace and diacritics, similarity ≥ 0.9). A failed quote → the evidence is removed → re-evaluate → probably abstain.
4. **Verdict strength is computed from explicit premises**, never from LLM self-confidence: source quality tier, freshness, quote-claim agreement, and the number of **independent** confirming publishers (see §7.3).
5. **Abstaining is a first-class outcome**, reached by rules (§7.3). We'd rather say "we don't know" than invent an answer.
6. **Technical statuses ≠ verdicts.** Errors, a missing key, rate limits, an unclear question or out-of-scope input get their own statuses and UI (brief §2, §5; scenario J).
7. **Determinism for consistency:** temperature 0, a fixed corpus version, and caching keyed by `hash(normalized_input, corpus_version, model_id)`.
8. **Swappable models and providers** through config only (brief §5 "Architektura").

---

## 5. Repo layout

```
/
├─ CONCEPT.md
├─ README.md                    # what it is, quick start (jury), architecture summary, limits
├─ docs/
│   ├─ ARCHITECTURE.md          # data flow, models, providers, limits (formal req.)
│   ├─ SOURCES.md               # sources, licenses, qualification/update/exclusion rules
│   ├─ RISKS.md                 # hallucinations, source bias, privacy, injection, availability, abuse
│   ├─ COSTS.md                 # cost of 1,000 queries, channel costs, scaling behaviour
│   └─ TEST_RESULTS.md          # metrics from §6 of the brief + how to reproduce
├─ backend/                     # uv project
│   ├─ pyproject.toml           # deps + [tool.ruff] + [tool.pytest]
│   ├─ uv.lock
│   ├─ src/prawdowid/
│   │   ├─ main.py              # app factory, routers, static web
│   │   ├─ config.py            # pydantic-settings
│   │   ├─ api/{checks,cases,sources,health,admin}.py
│   │   ├─ core/
│   │   │   ├─ pipeline.py      # orchestrates steps 0–9
│   │   │   ├─ normalize.py     # text / url / image
│   │   │   ├─ pii.py
│   │   │   ├─ claims.py        # extraction
│   │   │   ├─ retrieval.py     # hybrid search + rerank
│   │   │   ├─ judge.py         # evidence-only verdict
│   │   │   ├─ citations.py     # deterministic quote verification
│   │   │   ├─ strength.py      # explainable scoring + abstention rules
│   │   │   ├─ incidents.py     # incident-DB matching (context only)
│   │   │   ├─ source_status.py # neutral warnings (e.g. EU sanctions)
│   │   │   ├─ injection.py     # detection + event logging
│   │   │   └─ render.py        # plain-Polish answer
│   │   ├─ providers/{llm,embeddings,ocr}/{base,mock,...}.py
│   │   ├─ store/{db.py,models.py,migrations/}
│   │   ├─ cases/               # moderator loop (premium)
│   │   └─ prompts/*.md         # versioned prompts, no secrets
│   ├─ src/prawdowid/ingest/    # sources.yaml → corpus build CLI (`python -m prawdowid.ingest`)
│   ├─ eval/
│   │   ├─ cases.jsonl          # ≥ 30 own cases covering scenarios A–J
│   │   ├─ run_eval.py          # computes every required metric, writes TEST_RESULTS.md
│   │   └─ channel_consistency.py
│   └─ tests/
├─ channels/
│   ├─ discord_bot/             # uv project, calls the core API only
│   └─ demo_chat/               # simulated messenger adapter
├─ web/                         # React + Vite + TS
├─ mobile/                      # React Native (Expo) app: in-app input + share/context-menu entry points
│   ├─ app.config.ts            # intent filters (Android), share extension (iOS), API base URL
│   ├─ app/                     # Expo Router screens: index (input), result/[id], history, about
│   └─ src/{api,share,components}/ # API client (same contract as web), share-intent → CheckRequest mapping
├─ data/
│   ├─ sources.yaml             # OPEN source catalog (§6)
│   └─ corpus.sqlite            # built artifact (git-ignored; build script + prebuilt release asset)
├─ docker-compose.yml
└─ .env.example                 # every key documented, no real values
```

---

## 6. Sources & corpus

### 6.1 Requirements (brief §5 "Źródła")
- **≥ 100 documents/records, ≥ 10 domains, ≥ 2 source types.** Primary/official **and** credible secondary sources.
- The source list must be **auditable**: `data/sources.yaml` + `GET /v1/sources` + `docs/SOURCES.md`.
- Store **`published_at` and `retrieved_at`** for every document (brief "Aktualność").

### 6.2 Source types and candidates (verify the license and terms of each before ingesting)
| Type | Candidates |
|---|---|
| `official_primary` | gov.pl (MSZ, KPRM, ministries), BIP, ISAP (Polish legal acts), EUR-Lex, dane.gov.pl, GUS, official EU sites (europa.eu, consilium) |
| `fact_check` | IFCN/EFCSN-standard organizations, e.g. Demagog, AFP Sprawdzam, EDMO hubs |
| `disinfo_db` | EUvsDisinfo database, **the organizer's incident DB (JSON/CSV)**, NASK materials |
| `media_reference` | Public broadcasters / agency wires, **only where the terms allow storing excerpts** |

**Start with the organizer's source list** (published during the event on Discord) and their incident DB, then add the rest.

### 6.3 `sources.yaml` schema (open, swappable catalog: a premium point)
```yaml
- id: eurlex
  name: EUR-Lex
  publisher: Publications Office of the EU
  domain: eur-lex.europa.eu
  type: official_primary
  quality_tier: A            # A official/primary · B accredited fact-check · C reputable secondary
  license: "© EU, reuse authorised (verify per document)"
  store_mode: full_text      # full_text | excerpt_only | metadata_only (per license)
  update: manual|daily|weekly
  qualification: "Official EU legal database"
  excluded: false
  exclusion_reason: null
```
Qualification, update and exclusion rules are written in `docs/SOURCES.md`. `quality_tier` feeds the strength score but **never decides a verdict alone**.

### 6.4 Ingest pipeline (`uv run python -m prawdowid.ingest build`)
fetch (polite, robots.txt, rate-limited) → extract main text (trafilatura) → split into chunks of ~800–1,200 characters with overlap, keeping headings → record metadata (title, publisher, url, published_at, retrieved_at, language, type, tier, license) → index FTS5 (lowercase, diacritics both kept and folded) → embed → write `corpus_version`.
- Respect `store_mode`. For `excerpt_only`, keep the needed fragments plus the link, not full text.
- **No full-content archiving** without a legal basis, license, retention, access control and a deletion procedure (brief "Ograniczenia").

---

## 7. Contracts

### 7.1 Core API
`POST /v1/checks`
```json
{
  "channel": "web" | "discord" | "demo_chat" | "mobile",
  "session_id": "opaque-string",
  "input": { "type": "text" | "url" | "image", "text": "...", "url": "...", "image_b64": "..." }
}
```
`200 → CheckResult`
```json
{
  "check_id": "uuid",
  "status": "ok" | "needs_clarification" | "out_of_scope" | "technical_error" | "rate_limited",
  "status_message_pl": "…",                       // only for non-ok statuses
  "claims": [
    {
      "claim_id": "c1",
      "text": "the claim as understood, in Polish",
      "verdict": "potwierdzone" | "falszywe" | "wprowadzajace_w_blad" | "brak_wystarczajacych_dowodow" | "nie_podlega_weryfikacji",
      "explanation_pl": "2–4 simple sentences; every factual sentence ends with [n]",
      "strength": { "level": "wysoka" | "srednia" | "niska", "factors": { "independent_sources": 2, "best_tier": "A", "freshness_days": 12, "agreement": 0.92 } },
      "missing_context_pl": "… (scenario B)",
      "conflicts": [ { "summary_pl": "…", "citations": [2, 3] } ],
      "unresolved_pl": "what we could not establish (for abstentions)",
      "citations": [
        { "n": 1, "title": "…", "publisher": "…", "published_at": "2026-10-02", "retrieved_at": "2026-11-21",
          "url": "https://…", "quote": "verbatim fragment", "source_type": "official_primary", "archival": false }
      ],
      "context_notices": [ { "kind": "incident_match" | "source_status" | "archival_material", "text_pl": "…" } ]
    }
  ],
  "extracted_text_pl": "OCR transcript for image input (masked), else null",
  "input_notices_pl": ["e.g. instructions to the system were found in the input and ignored"],
  "limitations_pl": ["…"],
  "case": { "case_id": "uuid", "status": "zalecamy_przekazanie" | "przekazano_moderatorowi", "similar_reports": 2, "message_pl": "…" } | null,
  "model_info": { "llm": "provider/model", "corpus_version": "2026-11-21T10:00Z" },
  "latency_ms": 8400,
  "est_cost_usd": 0.004
}
```
Other endpoints: `GET /v1/checks/{id}` · `DELETE /v1/sessions/{session_id}` (deletes a demo session, brief "Prywatność") · `GET /v1/sources` · `GET /health` · `GET /metrics` (admin) · `POST /v1/cases`, `GET /v1/cases` (premium, admin) · `GET /v1/export?format=csv|json` (premium, admin).

### 7.2 Separating source material from interpretation (brief §2)
The UI and the bot always show two clearly separated blocks: **"Co mówią źródła"** (what the sources say: quotes + metadata) and **"Interpretacja Prawdowida"** (Prawdowid's interpretation: verdict + explanation + strength). They are never mixed.

### 7.3 Verdict & abstention rules (deterministic, after the judge)
- **The judge's input** contains only: the claim, the evidence chunks (with ids, metadata, `published_at`), and the system rules. **The output is JSON** following the schema: verdict, per-sentence `citation_ids`, verbatim quotes, `missing_context`, `conflicts`, `unresolved`.
- **Abstention gates.** Force `brak_wystarczajacych_dowodow` if any of these is true:
  - no evidence chunk passes the relevance threshold;
  - after citation verification, fewer than 1 valid quote supports the verdict;
  - a `potwierdzone`/`falszywe` verdict rests only on tier C sources;
  - the sources conflict and there's no higher-tier tie-breaker → report the conflict, no arbitrary certainty (scenario C);
  - the judge output fails schema validation twice.
- **`nie_podlega_weryfikacji`:** opinions, predictions and value judgements. The claim extractor marks these, and we explain fact vs opinion.
- **Strength level** = f(number of independent publishers, best tier, freshness relative to the claim's time, quote agreement). The rules are listed in `docs/ARCHITECTURE.md`, and the factors are shown to the user.
- **Archival material:** if the newest supporting evidence is older than N days for a time-sensitive claim → `archival_material` notice, preferring the newest data.
- **Incident match** (brief §3, scenario I): shown as context ("this content resembles a known incident: …"). **It never decides the verdict on its own**, and domain or channel presence alone is never a basis for a verdict.
- **Source status** (e.g. an entity under EU sanctions): a separate, neutral warning. **It never decides truth.**
- **High-risk / recurring unanswered questions:** create or update a moderator case (§9).

### 7.4 Failure handling (scenario J, brief "Zależności zewnętrzne")
A missing API key, a rate limit, an LLM/OCR/fetch failure or a timeout → `status: technical_error | rate_limited` with an honest Polish message ("Nie udało się wykonać sprawdzenia z powodu problemu technicznego. To nie jest ocena prawdziwości."). **Never return a verdict on a degraded path.** Log the error type.

### 7.5 Prompt-injection defences (scenario E; target ≥ 90%)
- Retrieved and user content goes into **data blocks with delimiters**, and the system prompt says that instructions inside data must be ignored.
- The judge and extractor have **no tools** and can't fetch URLs or change config. Strict JSON schema output, validated with pydantic.
- `injection.py`: heuristic + pattern detection on inputs and chunks (e.g. "ignore previous instructions", "zignoruj zasady", role-play headers, hidden text) → **log an `injection_attempt` event**. The answer continues normally, with an optional user notice.
- Output checks: the answer may only cite chunk ids that were provided. Unknown ids → fail → abstain.
- Eval covers injections in the user input, in a fetched URL page, and inside corpus documents.

### 7.6 Channel adapter contract
```python
class ChannelAdapter(Protocol):
    name: str
    async def to_check_request(self, platform_msg) -> CheckRequest: ...
    async def render(self, result: CheckResult) -> list[PlatformMessage]: ...
```
- **Discord:** `/sprawdz <text or link>` slash command + replies to DMs and mentions. Attachments go in as `image` (premium). Long answers are split. Citations are rendered as an embed list, with a link to the full result on the web.
- **Demo chat:** a minimal messenger-style page + webhook, so the brief's "adapter demonstracyjny" works with no external accounts.
- **Mobile app (React Native / Expo):** an **optional convenience channel**. The brief says citizens must not need to install specialised software (§1), so every feature also works on the web and Discord with no install. It is a thin client of the same `POST /v1/checks` API, rendering the same two blocks (§7.2) and the same technical statuses. Entry points, all mapped to one `CheckRequest` builder:
  - **In-app:** paste text or a link, or pick a screenshot from the gallery.
  - **System Share menu ("Udostępnij → Prawdowid"):** Android `ACTION_SEND` intent filters for `text/plain` and `image/*`; iOS Share Extension accepting text, URLs and images. A shared URL → `input.type = "url"`; shared plain text that is only a URL → `url`, otherwise `text`; a shared image → `image` (premium OCR path; resized/compressed on-device to fit the 5 MB limit).
  - **Text-selection context menu ("Sprawdź w Prawdowid"):** Android `ACTION_PROCESS_TEXT`, so a user can highlight a sentence in any app (browser, Messenger, Instagram comments) and check it directly. iOS has no third-party equivalent; there the Share menu covers it.
  - Shared content opens a **confirmation screen** first (shows exactly what will be sent; the user can edit or cancel) and is never sent automatically. Then it shows a progress state and the result, with a "Pokaż w przeglądarce" link to the full web result.
  - No verification logic, no LLM keys and no corpus on the device. `session_id` is a random id in secure storage, with a "Usuń moje dane" action calling `DELETE /v1/sessions/{id}`. The local history keeps only `check_id`s plus a short label.
  - Accessibility: system font scaling, screen-reader labels, WCAG AA contrast, plain-Polish copy (same strings as web where possible).

---

## 8. Privacy, security, observability

- **Data minimization:** store the masked input, claims, citation ids, verdicts, timings and cost. No raw images after processing (OCR text only, masked).
- **PII masking** before the LLM call **and** before storage.
- **Retention:** checks auto-delete after **30 days** (configurable), with `DELETE /v1/sessions/{id}`.
- **Security:** input validation and size limits (text ≤ 10k characters, image ≤ 5 MB), URL allowlist of schemes (http/https only), SSRF protection (block private IPs), rate limiting per session/IP/Discord user, secrets only via env, **no keys or personal data in the repo or demo materials**.
- **Event log:** `check_started/finished`, `abstained`, `technical_error`, `injection_attempt`, `retrieval_error`, `case_created`.
- **Metrics** (`/metrics` + admin dashboard, premium): latency p50/p95, model usage (tokens), retrieval errors, abstention rate, estimated cost per answer.
- **Transparency** (shown in the UI footer and README): which model and provider, where data is processed, corpus version, "AI-assisted; check the sources yourself".

---

## 9. Premium features (only after the gate passes)
Priority order (cost/benefit for the score):
1. **Screenshot / photo input** (scenario F): local Tesseract OCR → extract text + dates → the normal pipeline. Show the OCR text to the user and disclose limits ("odczyt może zawierać błędy"). Optional pHash match against images in the corpus/incident DB. **Never claim full reverse image search** without a working API.
2. **Evidence chain view:** claim → supporting / refuting / context evidence, as a visual list in the web UI.
3. **Information loop** (brief §2 says the system *should* notify a user designated by the admin about high-risk and recurring unanswered questions, so build at least a minimal version early): an unresolved check creates a moderator case. The admin configures the recipient (e.g. `MODERATOR_DISCORD_WEBHOOK_URL` or a moderators' Discord channel). "Przekazano" (handed over) is shown only after delivery to that recipient is confirmed. Similar questions are grouped (embedding similarity ≥ threshold + same claim cluster) into **one case** with a counter. An alert fires on N repeats. The UI clearly distinguishes "zalecamy przekazanie" (we recommend handing it over) from "przekazano moderatorowi" (handed to a moderator), and **never claims a handoff that didn't happen** (scenario H).
4. **Export** CSV/JSON of checks/cases; a note on mapping to DISARM / OpenCTI fields.
5. **Multilingual retrieval** (EN sources, PL answer): embeddings are already multilingual.
6. **Audio / video input** (brief §3 lists transcription): local `faster-whisper` → text → normal pipeline, with the transcript shown and limits disclosed. Low priority.
7. **Controlled archiving** of material the user points to (brief §3): only with a stated legal basis, license, retention, access control and deletion procedure (brief §5). Default: off, link + hash only.
8. **Self-hosted mode:** `LLM_PROVIDER=ollama` with a Polish open model. Documented as the "no non-EEA dependency" option.

---

## 10. Evaluation (brief §6)
- `eval/cases.jsonl`: **≥ 30 own cases**, at least 3 per scenario A–J (simple fact, missing context, conflict, no evidence, attack, multimodal, consistency, info loop, URL/incident, API limit). Each case has `input`, `expected_verdict | expected_status`, `expected_citation_urls`, and `notes`.
- The jury brings its own reference set (≥ 30 cases, brief §6). `run_eval.py --cases <file>` must accept it as-is (same JSONL/CSV shape, documented in `TEST_RESULTS.md`).
- `run_eval.py` computes every metric in §2 and writes `docs/TEST_RESULTS.md` + `eval/results.json` (reproducible: fixed corpus version, temperature 0, recorded model ids).
- Citation correctness = automatic quote verification + a **manual sample of 20** marked in `eval/manual_review.csv`.
- `channel_consistency.py` sends the same cases through the web API, the Discord adapter (test harness), the demo adapter and the mobile app's share-intent → `CheckRequest` mapping (unit-tested in `mobile/` against the same cases), and compares verdicts and citation sets.
- Scenario J runs with `LLM_PROVIDER=failing` (a mock that raises errors).
- **Never hard-code test answers in prompts or code** (brief §6). The jury will ask their own questions. List unsupported cases in `TEST_RESULTS.md`.

---

## 11. Deployment, costs, deliverables

**Jury quick start (must work as written):**
```bash
cp .env.example .env          # set LLM key (or LLM_PROVIDER=ollama), DISCORD_TOKEN optional
docker compose up --build     # builds corpus from release asset or runs ingest
# web:   http://localhost:8000
# demo chat adapter: http://localhost:8000/demo-chat
```
Plus a **public hosted demo URL**, an invite link for the Discord bot, and a downloadable **Android APK** of the mobile app (EAS build, attached to the GitHub release; iOS via TestFlight only if an Apple developer account is available). Access is free on the service side, and any operator fees are stated.

**`docs/COSTS.md`:** cost per check = tokens(extract + judge × claims) × price + embedding (local = 0) + hosting/1,000. Report the declared vs measured cost of 100 eval tests, plus Discord channel cost (free) and behaviour under load: caching, rate limits, horizontally scalable stateless API, SQLite → Postgres migration path.

**Formal deliverables checklist (brief §4):**
- [ ] Team name, title, description ≤ 4,000 characters
- [ ] PDF presentation ≤ 12 slides (problem, users, architecture, demo, test results, risks, next steps)
- [ ] Demo video ≤ 3 min (web + Discord + mobile Share-menu check + an abstention + an injection being ignored)
- [ ] Repo link + run instructions
- [ ] Architecture / data flow / models / providers / limits (`docs/ARCHITECTURE.md`)
- [ ] Sources, licenses, qualification & updates (`docs/SOURCES.md`)
- [ ] Test results per §6 + reproduction data (`docs/TEST_RESULTS.md`)
- [ ] Risks: hallucinations, source bias, privacy, prompt injection, availability, abuse (`docs/RISKS.md`)
- [ ] No API keys, personal data or secrets anywhere in the repo or materials

---

## 12. Milestones (24 h, parallel tracks)

**Track A: core (critical path)**
1. uv project, ruff, pytest, FastAPI skeleton, `/health`, mock LLM provider, `CheckResult` models.
2. Ingest pipeline + `sources.yaml` with **≥ 100 docs / ≥ 10 domains / ≥ 2 types** → `corpus.sqlite`.
3. Hybrid retrieval + tests.
4. Claim extraction → judge → citation verifier → strength + abstention rules → render.
5. Failure statuses, PII masking, injection detection, checks log, retention, delete session.

**Track B: channels**
6. Web UI (input, result view with the two separated blocks, statuses, accessibility).
7. Discord bot + demo chat adapter (both through the same API only).
7b. Mobile app (Expo): in-app input + result view first, then Android Share menu + text-selection menu, then iOS Share Extension. Not part of the gate (web + Discord cover it), so it must never block tracks A/C.

**Track C: quality**
8. `eval/cases.jsonl` (≥ 30) early, then iterate on the prompts and thresholds against the metrics.
9. Channel-consistency test, scenario J test, manual citation sample.

**Track D: delivery**
10. Docker Compose, `.env.example`, public deploy, docs (§11), slides, video.

**Then premium**, in §9 order.

---

## 13. Roadmap (post-hackathon, DO NOT IMPLEMENT now)
- Follow the brief's pilot path (§9): result reproduction → 4–6-week closed-corpus pilot with an expert queue → red-teaming → limited public launch → new channels/languages only after regression validation.
- WhatsApp Business / Messenger / SMS channels (they need accounts the organizer doesn't provide).
- **Mobile app, passive mode** (the earlier Android companion concept): an accessibility-service channel that reads posts in Instagram etc. and suggests checks. Share-to-check and the text-selection menu are **already in scope** (§7.6); only the passive reading is roadmap.
- SynthID watermark checks for images (the Google Content Detection API is partner-only as of Nov 2026), as a **context notice only**, never a verdict.
- Postgres + pgvector for a large corpus, scheduled source updates, human approval mode for published answers.

## 14. Rules for agents
- **The brief wins.** Re-read the relevant brief section before implementing a feature.
- **Never present LLM output as fact without a verified citation.** If the citation verifier fails, abstain.
- **Never invent sources, URLs, titles, dates or quotes**, including in tests, fixtures and demo data. Use real corpus documents.
- **Never decide a verdict from the domain, author, channel, popularity, share counts, sanctions status or the model's own label alone.**
- Channels contain **no verification logic**. They call the core API only.
- Technical failures produce a technical status, **never a verdict**.
- Never bypass paywalls, logins, robots.txt or anti-bot protections.
- Never hard-code eval answers or special-case test inputs.
- Python: uv only; ruff check + format + pytest must pass before every commit. Never commit secrets, `.env`, personal data, or a corpus that breaks licenses.
- Every external provider needs a mock; the eval and tests must run offline with mocks.
- User-facing text is **Polish, plain language** (aim for B1 level), short sentences.
- Don't add dependencies without a one-line justification in the commit.
- **Licenses must allow transferring the rights to MSZ** (Regulamin §4: the winners sign a copyright transfer and declare that the solution is free of legal defects). Prefer MIT/Apache/BSD code and models. Avoid non-commercial or unclear model licenses, and record each model's license in `docs/ARCHITECTURE.md`.
- If this document conflicts with a task or the brief, stop and flag it. Don't silently diverge.
# ARCHITECTURE

Brief §4 asks for the architecture, data flow, models, providers and main limits. The design rationale is in
`CONCEPT.md`. This file describes what is built.

## Components

```
channels (web · Discord · demo chat · mobile)  ──POST /v1/checks──▶  FastAPI (backend/src/prawdowid)
                                                                    │
  api/          checks, sessions, sources, health, admin            │
  core/         normalize → pii → injection → claims → retrieval → judge → citations → strength → render
  providers/    llm (openrouter, mistral, openai, anthropic, ollama, mock, failing) · embeddings · ocr · factcheck · notify
  corpus/       SQLite search index: documents, chunks, FTS5, vectors          ◀── ingest/ (sources.yaml → crawl → chunk → embed)
  store/        SQLite app DB: check log, events, cases
  cases/        information loop (grouping, alerts)
  channels/     shared chat renderer + ChannelAdapter protocol
```

## Data flow of one check

1. **Guard.** Pydantic validation: text ≤ 10k chars, image ≤ 5 MB, http/https URLs only, session id pattern. Rate limit per session and client.
2. **Normalize.** A text message that is only a link becomes a URL check. URL input is fetched with the SSRF guard (public IPs only, ports 80/443, re-checked on every redirect), robots.txt and a size limit, then trafilatura extracts the main text. Image input goes through local Tesseract OCR. A page that can't be fetched gives `needs_clarification`; an outage gives `technical_error`.
3. **Injection scan + PII mask.** Findings are logged as `injection_attempt` and shown to the user as a notice. Masking runs before the LLM call and before storage.
4. **Cache.** Key: `sha256(input_type, normalized masked text, corpus_version, model_id)`. A cached result is reused across channels. Results that create a moderator case aren't cached.
5. **Claim extraction (LLM).** Output: at most 5 claims, each with `kind` (fact / opinion / prediction), `search_query`, `time_reference` and `high_risk`. Opinions and predictions become `nie_podlega_weryfikacji` without a judge call.
6. **Retrieval.** FTS5 BM25 (Polish prefix stems, diacritics folded) plus cosine similarity, fused with RRF. Candidates must pass an absolute relevance score (lexical overlap + similarity) of at least `RETRIEVAL_MIN_RELEVANCE`. Optional Google Fact Check results are added as tier B/C evidence. Every passage is scanned for injection. If nothing passes, the claim abstains without a judge call.
7. **Judge (LLM).** Sees only the claim, the evidence passages (with ids and metadata) and today's date. Each data block is wrapped in a tag with a random per-call id, so content can't forge a closing delimiter. Output is a JSON schema with the verdict, verbatim quotes with stance, an explanation per sentence with evidence ids, conflicts, missing context and what stayed unresolved.
8. **Citation verifier (code).** Each quote must match its passage: normalized substring, or fuzzy partial ratio ≥ 90. Failed quotes and unknown ids are dropped, and the judge runs once more without the failed passages. Sentences citing anything that didn't verify are removed.
9. **Gates (code).** A decisive verdict falls back to `brak_wystarczajacych_dowodow` when there's no backing quote whose stance matches it, unknown ids were cited, only tier C sources back `potwierdzone`/`falszywe`, or sources conflict with no single higher-tier tie-breaker.
10. **Strength.** Computed from independent publishers, best tier, freshness and quote agreement, never from the model's confidence. Archival citations are flagged and lower the strength.
11. **Context notices.** Incident-DB match and source status. These never change the verdict.
12. **Cases.** Every unresolved factual claim creates a case or updates a similar one (embedding similarity ≥ 0.85). High-risk claims, and claims after N repeats, trigger the moderator webhook. The status becomes `przekazano_moderatorowi` only after a 2xx response.
13. **Persist.** The check log stores the masked input, statuses, verdicts, citation URLs, the full result, latency, tokens, cost, model and source collection version. Events go to the event log.

## Models and providers

| Role | Default | Alternatives | Where it runs |
|---|---|---|---|
| LLM (extract + judge) | `google/gemini-3.8-flash` via OpenRouter | `mistralai/mistral-large-4-0` via OpenRouter (EU vendor, ~4× slower), `mistral` direct (EU), `openai`, `anthropic`, `ollama` (self-hosted, e.g. Bielik) | OpenRouter (US intermediary, `data_collection: deny`) → model vendor |
| Embeddings | `hashing` (stems + char trigrams, offline) | `sentence_transformers` (e.g. `intfloat/multilingual-e5-base`) | local |
| OCR | Tesseract `pol+eng` | none | local |
| Fact-check DB | off | Google Fact Check Tools API | Google |
| Moderator alerts | off | Discord webhook | Discord |

All providers sit behind interfaces with mock or failing implementations, so tests and eval run without keys. The
temperature is 0 everywhere. Prompts are versioned in `prompts/*.md`.

**Model licenses** (needed for the rights transfer, Regulamin §4): the default stack uses no downloaded model weights.
If `sentence_transformers` is enabled, record the chosen model's license here before release (`docs/TODO.md`).

## Main limits

- The source collection covers safety, transport and government communications. Other topics are expected to abstain.
- The `hashing` embeddings are lexical-ish. Paraphrases with no shared words may be missed until a neural model is enabled.
- Client-side-rendered sources (gov.pl warnings, MSZ travel advisories) are pointers only.
- The rate limiter and cache live in process memory, so the API is single-instance until they move to a shared store.
- Images: text OCR only. No manipulation detection, no reverse image search.
- Audio and video input aren't supported.

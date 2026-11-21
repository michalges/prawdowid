# SOURCES.md: Prawdowid source catalog & rules

The machine-readable catalog is [`backend/data/sources.yaml`](../data/sources.yaml) (schema: CONCEPT §6.3). It is also served at `GET /v1/sources`.
It is seeded from the **organizer's example list** (MSZ challenge Discord). The organizer says these are examples and we don't have to implement all of them.

## 1. Coverage at a glance

| Area | Ingested (`listing` / `page`) | Pointer only (`live_link`) |
|---|---|---|
| Warnings & crisis management | gov.pl ostrzeżenia, RSO (MSWiA), RCB raport dobowy, RCB, MSWiA, KPRM | n/a |
| Foreign affairs / travel | MSZ informacje dla podróżujących | Odyseusz |
| Police, fire service, defence | Policja (KGP), Mazowiecka Policja, KG PSP, MON | n/a |
| Health, radiation, cyber | GIS ostrzeżenia, PAA, CERT Polska komunikaty | PAA monitoring, GIOŚ powietrze |
| Road | GDDKiA informacje drogowe + lista utrudnień, 19 111 | GDDKiA mapa |
| Rail | UTK pasażerowie, SOK | Portal Pasażera |
| Air | ULC, ULC prawa pasażera, MI prawa pasażerów | n/a |
| Sea & inland water | SAR, UM Gdynia, UM Szczecin warunki żeglugi, Wody Polskie komunikaty | IMGW Bałtyk |
| Weather & hydrology | n/a | IMGW meteo, IMGW hydro |
| Fact-checks (API) | Google Fact Check Tools (ClaimReview) | n/a |
| Disinformation DB (API, context only) | EUvsDisinfo | n/a |

**Brief minimum (§5 "Źródła"): ≥ 100 documents, ≥ 10 domains, ≥ 2 source types.**
- Domains: the catalog has 15+ distinct domains with ingestable content (gov.pl, policja.pl, mazowiecka.policja.gov.pl, moje.cert.pl, drogi.gddkia.gov.pl, ulc.gov.pl, utk.gov.pl, kgsok.pl, sar.gov.pl, umgdy.gov.pl, ums.gov.pl, …). ✅
- Documents: the `listing` sources (news and warnings archives) easily exceed 100 articles. ✅ Ingest enough history (e.g. the last 6–12 months) so that older claims are still checkable.
- Types: `official_primary` plus `fact_check` and `disinfo_db`, which currently come only through APIs. ⚠️ To be safe, also **ingest a static set of fact-check articles** (e.g. Demagog, AFP Sprawdzam) as `fact_check` documents, so the corpus itself has ≥ 2 types even when API keys are missing.

**Thematic gap:** the list is about safety, warnings and transport. Claims about politics, the economy, the EU or history need more sources from CONCEPT §6.2 (ISAP, EUR-Lex, GUS, europa.eu). The jury will ask their own questions, so out-of-corpus topics must **abstain**, not guess.

## 2. Fetch modes (how a source is used)

| `fetch_mode` | What we do | Can be cited? |
|---|---|---|
| `listing` | Crawl the index page (with pagination), ingest each linked article. `published_at` comes from the article, not the index. | Yes |
| `page` | Ingest one static reference page; re-fetch on `update`. | Yes |
| `live_link` | Dynamic dashboards, maps and apps (JS-rendered, constantly changing). **Not ingested.** Shown as "Aktualne dane sprawdzisz tutaj: …" in `limitations_pl`. | **No.** We have no stored quote, so it can never back a verdict. |
| `api` | Queried at check time through a provider interface with a mock (CONCEPT §3). | Depends on `use` |

`use`: `evidence` (can support or refute), `context_only` (context notice only, never decides a verdict), `pointer` (a link for the user).

## 3. Qualification, update & exclusion rules

**Qualification:** a source is admitted when **all** of these hold:
1. The publisher is identifiable: a public authority, a state agency or company acting in its official remit (tier A), or an IFCN/EFCSN-signatory fact-checker (tier B). Reputable secondary sources are tier C and can never decide `potwierdzone`/`falszywe` alone (CONCEPT §7.3).
2. Reuse terms allow storing what `store_mode` says. Polish public bodies' content is public sector information, but **check each site's terms** and set `license_verified: true` only after checking.
3. robots.txt allows fetching the paths we use. No logins, paywalls or anti-bot bypassing.
4. Pages have a recoverable publication or update date. Without one, the document is ingested with `published_at: null`, and an `archival_material` notice is shown if it's used for a time-sensitive claim.

**Update:**
- `daily` sources: re-crawl the index at least daily during the event (and before each eval run).
- `weekly`/`manual`: on demand.
- Each build writes a new `corpus_version`. Eval runs record it.
- Time-sensitive sources (road disruptions, warnings, navigation notices) use a short freshness window, so stale evidence triggers an archival notice instead of a confident verdict.

**Exclusion:**
- Set `excluded: true` + `exclusion_reason` (never delete the entry, for auditability) when the terms forbid reuse, robots.txt disallows it, the content isn't extractable without JS (then switch to `live_link`), or the source is found unreliable.
- Excluded sources' chunks are dropped at the next build.

## 4. External APIs

### Google Fact Check Tools API (`google_factcheck`)
- Use the `claims:search` endpoint with the claim text, `languageCode=pl`, plus an English query when the claim has an obvious international angle. Docs: <https://developers.google.com/fact-check/tools/api/reference/rest>.
- It returns `ClaimReview` items: claim text, claimant, the review's publisher, URL, date and **`textualRating`** (the fact-checker's own label).
- How we use it:
  - Each match becomes an evidence item of type `fact_check`, tier **B only if the publisher is an IFCN/EFCSN signatory**, otherwise C. Keep an allowlist in config.
  - The quote must come verbatim from the API response (the claim + rating) or from the fetched review page (if robots.txt allows it). The citation verifier treats these like any other chunk.
  - **The textual rating is not our verdict.** The judge compares the reviewed claim with the user's claim. If it's a different or only similar claim, the item is context, not evidence.
- Key: `GOOGLE_FACTCHECK_API_KEY`. No key or a quota error means the source is skipped and the gap is listed in `limitations_pl`. It's never a technical error for the whole check, as long as the corpus path still works.
- Mock: `providers/factcheck/mock.py` with recorded real responses (no invented reviews).

### EUvsDisinfo (`euvsdisinfo`)
- Bulk-download cases and articles using the organizer's guide: <https://euvsdisinfo.eu/public-docs/How_to_grab_all_Articles_and_Cases_from_disinfo.pdf>. The organizer offers tokens by DM if access is a problem.
- Stored as an **incident DB** (CONCEPT §7.3, scenario I). Matching uses embedding similarity between the claim and the case summary.
- Output is only a `context_notices[]` entry, `kind: "incident_match"`: "Podobna narracja pojawiła się we wrogich operacjach informacyjnych: …" with a link. **It never decides the verdict.**
- Token: `EUVSDISINFO_TOKEN`.

## 5. Pre-ingest checklist (per source)
- [ ] Open each URL; confirm the content is server-rendered (else `live_link`).
- [ ] Check robots.txt for the crawled paths.
- [ ] Read the terms / reuse notice; set `license`, `store_mode`, `license_verified: true`.
- [ ] Identify the date selector (published / updated) and the main-text extraction quality (trafilatura).
- [ ] Set a crawl depth and history window; respect rate limits (≥ 1 s between requests per host).

## 6. Environment keys

| Variable | Needed for | Required? |
|---|---|---|
| `GOOGLE_FACTCHECK_API_KEY` | Google Fact Check Tools API | Optional; it degrades gracefully |
| `EUVSDISINFO_TOKEN` | EUvsDisinfo download (if the endpoint requires it) | Optional; context only |

Both go in `backend/.env` (never committed). `backend/.env.example` documents them without values.

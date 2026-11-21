# SOURCES.md: Prawdowid source catalog & rules

The machine-readable catalog is [`backend/data/sources.yaml`](../backend/data/sources.yaml) (schema: CONCEPT §6.3). It is also served at `GET /v1/sources`.
It is seeded from the **organizer's example list** (MSZ challenge Discord). The organizer says these are examples and we don't have to implement all of them.

## 1. Coverage at a glance

The local demo corpus contains **116 documents across 12 distinct URL hostnames and two source
types**. This meets the brief's numerical minimum (100 documents, 10 domains and two types)
using the ingest CLI's hostname count. All 116 rows have `published_at` and `retrieved_at`
populated at date precision. Publication metadata can reflect a publisher's update date.

| Hostname | Type | Documents |
|---|---|---:|
| www.gov.pl | official_primary | 48 |
| kgsok.pl | official_primary | 15 |
| mazowiecka.policja.gov.pl | official_primary | 15 |
| policja.pl | official_primary | 15 |
| www.umgdy.gov.pl | official_primary | 9 |
| publikacje.new.stat.gov.pl | official_primary | 4 |
| demagog.org.pl | fact_check | 3 |
| ec.europa.eu | official_primary | 2 |
| poland.representation.ec.europa.eu | official_primary | 2 |
| commission.europa.eu | official_primary | 1 |
| moje.cert.pl | official_primary | 1 |
| ssgk.stat.gov.pl | official_primary | 1 |
| **Total** | **113 official_primary · 3 fact_check** | **116** |

The build extended the existing 102-document local seed. Its legacy licence flags still need
a per-source review before redistribution. The 14 new documents use verified terms and curated
`page` entries so the dated evidence stays addressable. The two GUS hosts share a publisher,
as do the Commission and its Polish Representation. Hostname count measures corpus coverage.
It does not establish publisher independence.

### Rebuild and audit the expansion

Run from `backend/` with the demo seed in `data/corpus.sqlite`.

```sh
uv run python -m prawdowid.ingest build --only cert_komunikaty,gus_cpi,gus_economic_review,commission_news,commission_poland_news,eurostat_inflation,demagog_reviews,eli_acts
uv run python -m prawdowid.ingest stats
```

The catalog and `GET /v1/sources` list source entries and reuse terms. The SQLite
`documents` table records each ingested URL, publisher, licence, source type and dates.
The development SQLite file is gitignored.

### Source checks on 2026-11-21

| Publisher and scope | Robots and extraction | Reuse |
|---|---|---|
| GUS price and GDP releases | [Publications robots](https://publikacje.new.stat.gov.pl/robots.txt) allows the selected pages. The [monthly review robots URL](https://ssgk.stat.gov.pl/robots.txt) returned 404. Both hosts published usable text and dates. | Attribute GUS and the source URL. [Copyright notice](https://stat.gov.pl/copyright) |
| European Commission and its Polish Representation | The [Commission](https://commission.europa.eu/robots.txt) and [Representation](https://poland.representation.ec.europa.eu/robots.txt) allow the selected paths. The extracted dates and text came from Polish-language pages. | CC BY 4.0 for EU-owned text, with attribution and indication of changes. [Legal notice](https://commission.europa.eu/legal-notice_pl) |
| Eurostat releases | [Robots](https://ec.europa.eu/robots.txt) allows the selected press releases. The two English-language releases had dates and usable prose. | Attribute Eurostat. EU-owned editorial content is CC BY 4.0. [Reuse notice](https://ec.europa.eu/eurostat/help/copyright-notice) |
| CERT Polska advisory | [Robots](https://moje.cert.pl/robots.txt) explicitly allows `/komunikaty/` despite the general disallow. The selected advisory supplied text and a date. | CC BY-SA 4.0 for advisories, as stated in the footer. [Source advisory](https://moje.cert.pl/komunikaty/2026/73/prosba-o-wycene-ale-towarem-jest-dostep-do-twojego-komputera/) |
| Demagog | [Robots](https://demagog.org.pl/robots.txt) allows the selected articles, signals reference use and disallows AI training. All three articles supplied text and dates. | The local noncommercial demo keeps excerpts with the publisher and original URL. [Reuse terms](https://demagog.org.pl/zasady-udostepniania-tresci/) · [Methodology and IFCN/EFCSN membership](https://demagog.org.pl/metodologia/) |

### Skipped candidates

| Candidate | Reason |
|---|---|
| PAP | The publisher expressly reserves text and data mining rights. [Terms §1.5](https://www.pap.pl/regulamin) |
| ISAP and UTK | Their robots files disallow general crawlers. [ISAP robots](https://isap.sejm.gov.pl/robots.txt) · [UTK robots](https://utk.gov.pl/robots.txt) |
| ELI | Robots allowed the URL and the official act is outside copyright under Article 4. The HTML extractor retained the table of contents and inferred an unrelated date, so the candidate was removed. [Official act](https://eli.gov.pl/eli/DU/2023/1524/ogl) · [Article 4](https://eli.gov.pl/api/acts/DU/2021/1062/text.html) |
| Legacy GUS URL | The old publication URL returned 404. GUS's new Publications portal carries the release. |
| ULC, Consilium and EUR-Lex | ULC served a challenge page, Consilium returned 403, and EUR-Lex returned an empty 202 for robots.txt. |
| dane.gov.pl | The tested robots URL returned the app's HTML shell. The portal was deferred pending a verifiable dataset source and its reuse terms. |
| NBP | The robots request timed out. |
| Fakenews.pl and PKP Intercity | Robots allowed access. Reuse permission for indexed text was not verified. |
| EUvsDisinfo | Deferred to the existing context-only incident import. This build did not establish reuse terms for a static copy of case text. [About the database](https://euvsdisinfo.eu/about/) |

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

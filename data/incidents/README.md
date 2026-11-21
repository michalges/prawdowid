# Incident database

Put the organizer's incident DB export and EUvsDisinfo exports here as `*.jsonl`, `*.json` or `*.csv`.
The API loads them at startup (`backend/src/prawdowid/core/incidents.py`).

Recognised fields (extra fields are ignored): `id`, `title` (or `name`), `summary` (or `description` / `text`),
`date` (or `published_at`), `url`, `source`, `license`.

A match is shown only as a context notice ("Ta treść przypomina znany przypadek…"). It never decides a verdict
(brief §3, scenario I). Don't commit files whose license doesn't allow redistribution. Record each file's license
in `docs/SOURCES.md`.

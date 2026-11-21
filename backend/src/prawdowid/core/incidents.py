"""Known-incident matching (brief §3, scenario I). The match is shown as context only and never
decides a verdict. Records come from the organizer's incident DB / EUvsDisinfo exports in
data/incidents/ (*.jsonl or *.csv)."""

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from prawdowid.core.extract import get_parsed_date
from prawdowid.core.text import get_lexical_overlap
from prawdowid.providers.embeddings.base import EmbeddingMatrix, EmbeddingProvider
from prawdowid.schemas import ContextNotice, ContextNoticeKind

MIN_SIMILARITY = 0.55
MIN_OVERLAP = 0.35


@dataclass(frozen=True)
class Incident:
    incident_id: str
    title: str
    summary: str
    published_at: date | None
    url: str | None
    source: str
    license: str | None


def get_incident(record: dict, default_source: str) -> Incident | None:
    title = (record.get("title") or record.get("name") or "").strip()
    summary = (
        record.get("summary") or record.get("description") or record.get("text") or ""
    ).strip()
    if not title and not summary:
        return None
    return Incident(
        incident_id=str(record.get("id") or record.get("incident_id") or title[:40]),
        title=title or summary[:80],
        summary=summary or title,
        published_at=get_parsed_date(record.get("date") or record.get("published_at")),
        url=record.get("url"),
        source=record.get("source") or default_source,
        license=record.get("license"),
    )


def load_incidents(directory: Path) -> list[Incident]:
    incidents: list[Incident] = []
    if not directory.exists():
        return incidents
    for path in sorted(directory.iterdir()):
        if path.suffix == ".jsonl":
            records = [
                json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()
            ]
        elif path.suffix == ".json":
            loaded = json.loads(path.read_text("utf-8"))
            records = loaded if isinstance(loaded, list) else loaded.get("items", [])
        elif path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as handle:
                records = list(csv.DictReader(handle))
        else:
            continue
        incidents += [item for record in records if (item := get_incident(record, path.stem))]
    return incidents


@dataclass
class IncidentMatcher:
    incidents: list[Incident]
    embedder: EmbeddingProvider
    vectors: EmbeddingMatrix

    @classmethod
    def load(cls, directory: Path, embedder: EmbeddingProvider) -> "IncidentMatcher":
        incidents = load_incidents(directory)
        texts = [f"{item.title}. {item.summary}" for item in incidents]
        vectors = embedder.embed(texts, "passage") if texts else np.zeros((0, 1), dtype=np.float32)
        return cls(incidents=incidents, embedder=embedder, vectors=vectors)

    def get_notices(self, text: str) -> list[ContextNotice]:
        if not self.incidents:
            return []
        similarities = self.vectors @ self.embedder.embed([text], "query")[0]
        best_index = int(np.argmax(similarities))
        incident = self.incidents[best_index]
        overlap = get_lexical_overlap(f"{incident.title} {incident.summary}", text)
        if similarities[best_index] < MIN_SIMILARITY or overlap < MIN_OVERLAP:
            return []
        when = f", {incident.published_at.isoformat()}" if incident.published_at else ""
        link = f" Więcej: {incident.url}" if incident.url else ""
        return [
            ContextNotice(
                kind=ContextNoticeKind.INCIDENT_MATCH,
                text_pl=(
                    f"Ta treść przypomina znany przypadek dezinformacji: „{incident.title}” "
                    f"({incident.source}{when}). To tylko kontekst: samo podobieństwo nie "
                    f"przesądza o prawdziwości tej treści.{link}"
                ),
            )
        ]

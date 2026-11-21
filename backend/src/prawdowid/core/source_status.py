"""Neutral source-status warnings (brief §5 "Ograniczenia"): shown separately, never a verdict."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, TypeAdapter

from prawdowid.schemas import ContextNotice, ContextNoticeKind


class SourceStatusEntry(BaseModel):
    domain: str
    status_pl: str
    reference_url: str
    checked_at: str
    verified: bool


@dataclass
class SourceStatusRegistry:
    entries: list[SourceStatusEntry]

    @classmethod
    def load(cls, path: Path) -> "SourceStatusRegistry":
        if not path.exists():
            return cls(entries=[])
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        entries = TypeAdapter(list[SourceStatusEntry]).validate_python(raw)
        return cls(entries=[entry for entry in entries if entry.verified])

    def get_notices(self, url: str | None) -> list[ContextNotice]:
        host = (urlsplit(url).hostname or "").lower() if url else ""
        if not host:
            return []
        return [
            ContextNotice(
                kind=ContextNoticeKind.SOURCE_STATUS,
                text_pl=(
                    f"Informacja o źródle {entry.domain}: {entry.status_pl} "
                    f"(podstawa: {entry.reference_url}, sprawdzono {entry.checked_at}). "
                    "To ostrzeżenie o statusie źródła, a nie ocena prawdziwości tej treści."
                ),
            )
            for entry in self.entries
            if host == entry.domain or host.endswith(f".{entry.domain}")
        ]

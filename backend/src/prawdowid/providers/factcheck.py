"""Google Fact Check Tools API (ClaimReview) as an optional, live evidence source."""

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import httpx

from prawdowid.core.evidence import Evidence
from prawdowid.core.extract import get_parsed_date
from prawdowid.schemas import QualityTier, SourceType

GOOGLE_FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
MAX_REVIEWS = 3


class FactCheckError(Exception):
    pass


class FactCheckProvider(Protocol):
    @property
    def is_enabled(self) -> bool: ...

    async def search(self, claim: str) -> list[Evidence]: ...


@dataclass(frozen=True)
class ClaimReviewItem:
    claim_text: str
    claimant: str | None
    publisher: str
    url: str
    title: str
    review_date: date | None
    textual_rating: str


def get_review_items(payload: dict) -> list[ClaimReviewItem]:
    items: list[ClaimReviewItem] = []
    for claim in payload.get("claims", []):
        for review in claim.get("claimReview", []):
            if not review.get("url") or not review.get("textualRating"):
                continue
            items.append(
                ClaimReviewItem(
                    claim_text=claim.get("text", ""),
                    claimant=claim.get("claimant"),
                    publisher=(review.get("publisher") or {}).get("name")
                    or (review.get("publisher") or {}).get("site")
                    or "nieznany wydawca",
                    url=review["url"],
                    title=review.get("title") or claim.get("text", ""),
                    review_date=get_parsed_date(review.get("reviewDate")),
                    textual_rating=review["textualRating"],
                )
            )
    return items


def get_review_evidence(items: list[ClaimReviewItem], allowlist: set[str]) -> list[Evidence]:
    """The evidence text is built only from fields the API returned, so quotes stay verifiable.
    The rating is the fact-checker's label, never our verdict (docs/SOURCES.md §4)."""
    today = datetime.now(UTC).date()
    return [
        Evidence(
            evidence_id=f"f{i + 1}",
            text=(
                f'Sprawdzane twierdzenie: "{item.claim_text}". '
                f"Ocena weryfikatora {item.publisher}: {item.textual_rating}. {item.title}"
            ),
            title=item.title,
            publisher=item.publisher,
            url=item.url,
            published_at=item.review_date,
            retrieved_at=today,
            source_type=SourceType.FACT_CHECK,
            quality_tier=QualityTier.B if item.publisher.lower() in allowlist else QualityTier.C,
            source_id="google_factcheck",
            relevance=0.0,
        )
        for i, item in enumerate(items[:MAX_REVIEWS])
    ]


@dataclass
class DisabledFactCheckProvider:
    @property
    def is_enabled(self) -> bool:
        return False

    async def search(self, claim: str) -> list[Evidence]:
        return []


@dataclass
class GoogleFactCheckProvider:
    api_key: str
    publisher_allowlist: set[str]
    timeout_s: float = 8.0
    transport: httpx.AsyncBaseTransport | None = None

    @property
    def is_enabled(self) -> bool:
        return True

    async def search(self, claim: str) -> list[Evidence]:
        params = {"query": claim[:500], "languageCode": "pl", "pageSize": 5, "key": self.api_key}
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, transport=self.transport
            ) as client:
                response = await client.get(GOOGLE_FACTCHECK_URL, params=params)
        except httpx.HTTPError as error:
            raise FactCheckError(type(error).__name__) from error
        if response.status_code != 200:
            raise FactCheckError(f"HTTP {response.status_code}")
        return get_review_evidence(get_review_items(response.json()), self.publisher_allowlist)


@dataclass
class RecordedFactCheckProvider:
    """Replays recorded real API responses (JSON files) for offline tests. Never invented data."""

    responses_by_query: dict[str, dict] = field(default_factory=dict)
    publisher_allowlist: set[str] = field(default_factory=set)

    @classmethod
    def from_file(cls, path: Path, allowlist: set[str]) -> "RecordedFactCheckProvider":
        return cls(json.loads(path.read_text(encoding="utf-8")), allowlist)

    @property
    def is_enabled(self) -> bool:
        return True

    async def search(self, claim: str) -> list[Evidence]:
        payload = self.responses_by_query.get(claim, {})
        return get_review_evidence(get_review_items(payload), self.publisher_allowlist)

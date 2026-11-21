from datetime import date

from pydantic import BaseModel

from prawdowid.schemas import QualityTier, SourceType


class Evidence(BaseModel):
    """A retrieved, citable passage. `evidence_id` (e1, e2, …) is the only handle the judge sees."""

    evidence_id: str
    text: str
    title: str
    publisher: str
    url: str
    published_at: date | None
    retrieved_at: date
    source_type: SourceType
    quality_tier: QualityTier
    source_id: str
    relevance: float
    time_sensitive: bool = False
    chunk_id: int | None = None

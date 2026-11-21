from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from prawdowid.schemas import QualityTier, SourceType


class FetchMode(StrEnum):
    LISTING = "listing"
    PAGE = "page"
    LIVE_LINK = "live_link"
    API = "api"


class SourceUse(StrEnum):
    EVIDENCE = "evidence"
    CONTEXT_ONLY = "context_only"
    POINTER = "pointer"


class StoreMode(StrEnum):
    FULL_TEXT = "full_text"
    EXCERPT_ONLY = "excerpt_only"
    METADATA_ONLY = "metadata_only"


class SourceEntry(BaseModel):
    """One row of backend/data/sources.yaml (CONCEPT §6.3, docs/SOURCES.md)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    publisher: str
    domain: str
    urls: list[HttpUrl] = Field(min_length=1)
    type: SourceType
    quality_tier: QualityTier
    fetch_mode: FetchMode
    use: SourceUse
    store_mode: StoreMode
    update: str
    license: str
    license_verified: bool
    qualification: str
    notes: str | None = None
    excluded: bool
    exclusion_reason: str | None
    time_sensitive: bool = False
    max_documents: int = 60
    keywords: list[str] = Field(default_factory=list)

    @property
    def is_ingestable(self) -> bool:
        return (
            not self.excluded
            and self.fetch_mode in (FetchMode.LISTING, FetchMode.PAGE)
            and self.store_mode is not StoreMode.METADATA_ONLY
        )


class CorpusDocument(BaseModel):
    source_id: str
    url: str
    title: str
    publisher: str
    published_at: date | None
    retrieved_at: date
    language: str = "pl"
    source_type: SourceType
    quality_tier: QualityTier
    license: str
    text: str


class CorpusChunk(BaseModel):
    chunk_id: int
    document_id: int
    source_id: str
    url: str
    title: str
    publisher: str
    published_at: date | None
    retrieved_at: date
    source_type: SourceType
    quality_tier: QualityTier
    text: str
    time_sensitive: bool = False

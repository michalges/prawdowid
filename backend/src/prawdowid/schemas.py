"""Public API contract (CONCEPT §7.1). Channels speak only these models."""

from datetime import date
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

MAX_TEXT_CHARS = 10_000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_B64_CHARS = (MAX_IMAGE_BYTES * 4) // 3 + 4


class Channel(StrEnum):
    WEB = "web"
    DISCORD = "discord"
    DEMO_CHAT = "demo_chat"
    MOBILE = "mobile"


class InputType(StrEnum):
    TEXT = "text"
    URL = "url"
    IMAGE = "image"


class CheckStatus(StrEnum):
    OK = "ok"
    NEEDS_CLARIFICATION = "needs_clarification"
    OUT_OF_SCOPE = "out_of_scope"
    TECHNICAL_ERROR = "technical_error"
    RATE_LIMITED = "rate_limited"


class Verdict(StrEnum):
    CONFIRMED = "potwierdzone"
    FALSE = "falszywe"
    MISLEADING = "wprowadzajace_w_blad"
    INSUFFICIENT_EVIDENCE = "brak_wystarczajacych_dowodow"
    NOT_VERIFIABLE = "nie_podlega_weryfikacji"


class StrengthLevel(StrEnum):
    HIGH = "wysoka"
    MEDIUM = "srednia"
    LOW = "niska"


class SourceType(StrEnum):
    OFFICIAL_PRIMARY = "official_primary"
    FACT_CHECK = "fact_check"
    DISINFO_DB = "disinfo_db"
    MEDIA_REFERENCE = "media_reference"


class QualityTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class ContextNoticeKind(StrEnum):
    INCIDENT_MATCH = "incident_match"
    SOURCE_STATUS = "source_status"
    ARCHIVAL_MATERIAL = "archival_material"


class CaseStatus(StrEnum):
    RECOMMENDED = "zalecamy_przekazanie"
    HANDED_OVER = "przekazano_moderatorowi"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckInput(StrictModel):
    type: InputType
    text: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
    url: HttpUrl | None = None
    image_b64: str | None = Field(default=None, max_length=MAX_IMAGE_B64_CHARS)

    @model_validator(mode="after")
    def check_payload_matches_type(self) -> Self:
        payload_by_type = {
            InputType.TEXT: self.text,
            InputType.URL: self.url,
            InputType.IMAGE: self.image_b64,
        }
        if not payload_by_type[self.type]:
            raise ValueError(f"input.type={self.type.value} requires the matching field")
        if self.type is InputType.TEXT and self.text is not None and not self.text.strip():
            raise ValueError("input.text must not be blank")
        return self


class CheckRequest(StrictModel):
    channel: Channel
    session_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    input: CheckInput


class StrengthFactors(StrictModel):
    independent_sources: int = Field(ge=0)
    best_tier: QualityTier | None
    freshness_days: int | None = Field(default=None, ge=0)
    agreement: float = Field(ge=0, le=1)


class Strength(StrictModel):
    level: StrengthLevel
    factors: StrengthFactors


class Citation(StrictModel):
    n: int = Field(ge=1)
    title: str
    publisher: str
    published_at: date | None
    retrieved_at: date
    url: HttpUrl
    quote: str
    source_type: SourceType
    archival: bool = False


class Conflict(StrictModel):
    summary_pl: str
    citations: list[int]


class ContextNotice(StrictModel):
    kind: ContextNoticeKind
    text_pl: str


class ClaimResult(StrictModel):
    claim_id: str
    text: str
    verdict: Verdict
    explanation_pl: str
    strength: Strength | None = None
    missing_context_pl: str | None = None
    conflicts: list[Conflict] = Field(default_factory=list)
    unresolved_pl: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    context_notices: list[ContextNotice] = Field(default_factory=list)


class ModelInfo(StrictModel):
    llm: str
    corpus_version: str | None


class CaseInfo(StrictModel):
    """Information loop (brief §5 "Pętla informacji"). A recommendation is never shown as a
    handoff."""

    case_id: UUID
    status: CaseStatus
    similar_reports: int = Field(ge=1)
    message_pl: str


class CheckResult(StrictModel):
    check_id: UUID = Field(default_factory=uuid4)
    status: CheckStatus
    status_message_pl: str | None = None
    claims: list[ClaimResult] = Field(default_factory=list)
    extracted_text_pl: str | None = None
    input_notices_pl: list[str] = Field(default_factory=list)
    limitations_pl: list[str] = Field(default_factory=list)
    case: CaseInfo | None = None
    model_info: ModelInfo
    latency_ms: int = Field(ge=0)
    est_cost_usd: float = Field(ge=0)

    @model_validator(mode="after")
    def check_status_consistency(self) -> Self:
        """Technical statuses never carry verdicts (CONCEPT §7.4)."""
        if self.status is CheckStatus.OK:
            if self.status_message_pl is not None:
                raise ValueError("status_message_pl is only for non-ok statuses")
        else:
            if self.claims:
                raise ValueError(f"status={self.status.value} must not carry claims/verdicts")
            if not self.status_message_pl:
                raise ValueError(f"status={self.status.value} requires status_message_pl")
        return self


class HealthResponse(StrictModel):
    status: Literal["ok"]
    version: str
    llm_provider: str
    corpus_version: str | None
    corpus_chunks: int
    embedding_model: str
    ocr: str
    factcheck_enabled: bool
    moderator_notifications: bool
    data_processing_pl: str


class SessionDeletion(StrictModel):
    session_id: str
    deleted: dict[str, int]


class SourceInfo(StrictModel):
    id: str
    name: str
    publisher: str
    domain: str
    urls: list[str]
    type: SourceType
    quality_tier: QualityTier
    fetch_mode: str
    use: str
    license: str
    license_verified: bool
    qualification: str
    excluded: bool
    exclusion_reason: str | None
    documents: int


class SourceCatalog(StrictModel):
    corpus_version: str | None
    documents: int
    chunks: int
    sources: list[SourceInfo]

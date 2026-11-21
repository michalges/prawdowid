from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from prawdowid.providers.llm.base import (
    DataBlock,
    LLMConfigError,
    LLMOutputError,
    LLMUnavailableError,
    LLMUsage,
)

type MockResponder = Callable[[str, list[DataBlock], type[BaseModel]], dict]

OFFLINE_MODEL_ID = "mock/offline"


@dataclass(frozen=True)
class RecordedCall:
    system: str
    data_blocks: list[DataBlock]
    schema: type[BaseModel]


@dataclass
class MockLLMProvider:
    """Offline, deterministic provider. `responder` returns the raw JSON object for a call, the
    same way a real model would, and it's validated against the schema like real output."""

    responder: MockResponder | None = None
    reported_model_id: str = "mock/deterministic"
    calls: list[RecordedCall] = field(default_factory=list)

    @property
    def model_id(self) -> str:
        return self.reported_model_id

    async def generate_json[T: BaseModel](
        self, *, system: str, data_blocks: list[DataBlock], schema: type[T]
    ) -> tuple[T, LLMUsage]:
        self.calls.append(RecordedCall(system=system, data_blocks=data_blocks, schema=schema))
        if self.responder is None:
            raise LLMConfigError("Mock LLM has no responder configured")
        raw_output = self.responder(system, data_blocks, schema)
        try:
            parsed = schema.model_validate(raw_output)
        except ValidationError as error:
            raise LLMOutputError(str(error)) from error
        return parsed, LLMUsage()


@dataclass
class FailingLLMProvider:
    """Always fails. It drives scenario J (API outage) in tests and eval."""

    error: Exception = field(default_factory=lambda: LLMUnavailableError("Simulated LLM outage"))
    reported_model_id: str = "failing/simulated"

    @property
    def model_id(self) -> str:
        return self.reported_model_id

    async def generate_json[T: BaseModel](
        self, *, system: str, data_blocks: list[DataBlock], schema: type[T]
    ) -> tuple[T, LLMUsage]:
        raise self.error


OPINION_MARKERS = (
    "uważam",
    "moim zdaniem",
    "powinien",
    "powinna",
    "powinno",
    "najlepsz",
    "najgorsz",
)
PREDICTION_MARKERS = ("będzie", "będą", "wkrótce", "jutro", "w przyszłym")
CONTENT_LABELS = ("user_input", "url_content", "ocr_text")
MIN_CLAIM_WORDS = 4
OFFLINE_NOTE_PL = (
    "Tryb offline bez modelu językowego: system nie porównał treści dowodów, "
    "więc nie wydaje werdyktu."
)


def get_offline_claim(sentence: str) -> dict:
    lowered = sentence.lower()
    kind = "fact"
    if any(marker in lowered for marker in OPINION_MARKERS):
        kind = "opinion"
    elif any(marker in lowered for marker in PREDICTION_MARKERS):
        kind = "prediction"
    return {
        "text": sentence[:600],
        "kind": kind,
        "search_query": sentence[:300],
        "time_reference": None,
        "high_risk": False,
    }


def get_offline_extraction(data_blocks: list[DataBlock]) -> dict:
    from prawdowid.core.text import split_sentences

    content = " ".join(block.content for block in data_blocks if block.label in CONTENT_LABELS)
    sentences = [s for s in split_sentences(content) if len(s.split()) >= MIN_CLAIM_WORDS]
    if not sentences:
        return {
            "status": "needs_clarification",
            "message_pl": "Napisz, jakie konkretnie twierdzenie mamy sprawdzić.",
            "claims": [],
        }
    return {
        "status": "ok",
        "message_pl": None,
        "claims": [get_offline_claim(sentence) for sentence in sentences[:3]],
    }


def get_offline_judgement() -> dict:
    return {
        "verdict": "brak_wystarczajacych_dowodow",
        "quotes": [],
        "explanation": [{"text": OFFLINE_NOTE_PL, "evidence_ids": []}],
        "missing_context_pl": None,
        "conflicts": [],
        "unresolved_pl": OFFLINE_NOTE_PL,
    }


def get_offline_responder() -> MockResponder:
    """Deterministic keyless behaviour: heuristic claim splitting, and always abstaining at the
    judge step (with an explicit note), so the offline path never invents a verdict."""

    def respond(system: str, data_blocks: list[DataBlock], schema: type[BaseModel]) -> dict:
        if schema.__name__ == "ClaimExtraction":
            return get_offline_extraction(data_blocks)
        if schema.__name__ == "JudgeOutput":
            return get_offline_judgement()
        raise LLMConfigError(f"offline responder has no rule for {schema.__name__}")

    return respond

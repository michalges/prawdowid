from datetime import date

import pytest
from pydantic import ValidationError

from prawdowid.schemas import (
    CheckResult,
    CheckStatus,
    Citation,
    ClaimResult,
    ModelInfo,
    SourceType,
    Verdict,
)

MODEL_INFO = ModelInfo(llm="mock/deterministic", corpus_version=None)


def get_claim() -> ClaimResult:
    return ClaimResult(
        claim_id="c1",
        text="Twierdzenie testowe",
        verdict=Verdict.INSUFFICIENT_EVIDENCE,
        explanation_pl="Nie znaleźliśmy źródeł.",
        unresolved_pl="Brak publikacji na ten temat.",
    )


def test_technical_status_cannot_carry_verdicts() -> None:
    with pytest.raises(ValidationError, match="must not carry claims"):
        CheckResult(
            status=CheckStatus.TECHNICAL_ERROR,
            status_message_pl="Błąd techniczny.",
            claims=[get_claim()],
            model_info=MODEL_INFO,
            latency_ms=1,
            est_cost_usd=0,
        )


def test_non_ok_status_requires_message() -> None:
    with pytest.raises(ValidationError, match="requires status_message_pl"):
        CheckResult(
            status=CheckStatus.OUT_OF_SCOPE, model_info=MODEL_INFO, latency_ms=1, est_cost_usd=0
        )


def test_ok_result_serializes_verdict_values_in_polish() -> None:
    result = CheckResult(
        status=CheckStatus.OK,
        claims=[get_claim()],
        model_info=MODEL_INFO,
        latency_ms=5,
        est_cost_usd=0,
    )

    dumped = result.model_dump(mode="json")

    assert dumped["claims"][0]["verdict"] == "brak_wystarczajacych_dowodow"


def test_citation_requires_http_url() -> None:
    with pytest.raises(ValidationError):
        Citation(
            n=1,
            title="t",
            publisher="p",
            published_at=None,
            retrieved_at=date(2026, 11, 21),
            url="javascript:alert(1)",
            quote="q",
            source_type=SourceType.OFFICIAL_PRIMARY,
        )

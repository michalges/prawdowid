"""Builds the plain-Polish ClaimResult: source material and interpretation kept separate."""

from datetime import date, timedelta

from prawdowid.core.citations import VerifiedJudgement, VerifiedQuote
from prawdowid.core.claims import ExtractedClaim
from prawdowid.core.strength import GateDecision
from prawdowid.schemas import (
    Citation,
    ClaimResult,
    Conflict,
    ContextNotice,
    ContextNoticeKind,
    Strength,
    Verdict,
)

DEFAULT_EXPLANATIONS = {
    Verdict.INSUFFICIENT_EVIDENCE: (
        "Nie znaleźliśmy w naszych źródłach informacji, które pozwalają to rozstrzygnąć."
    ),
    Verdict.NOT_VERIFIABLE: (
        "To jest opinia, ocena albo przewidywanie, a nie fakt, który da się sprawdzić w źródłach."
    ),
}
NO_EVIDENCE_UNRESOLVED_PL = (
    "Nie wiemy, czy to prawda: w katalogu źródeł nie ma dokumentów na ten temat."
)


def get_citations(
    verified: VerifiedJudgement,
    today: date,
    archival_after: timedelta,
    time_sensitive_after: timedelta,
) -> tuple[list[Citation], dict[str, int], bool]:
    """One citation per distinct evidence item with a verified quote, numbered in order of use."""
    numbers: dict[str, int] = {}
    first_quotes: dict[str, VerifiedQuote] = {}
    ordered_ids = [eid for sentence in verified.sentences for eid in sentence.evidence_ids]
    ordered_ids += [quote.evidence.evidence_id for quote in verified.quotes]
    for quote in verified.quotes:
        first_quotes.setdefault(quote.evidence.evidence_id, quote)
    citations: list[Citation] = []
    has_archival = False
    for evidence_id in dict.fromkeys(ordered_ids):
        quote = first_quotes.get(evidence_id)
        if quote is None:
            continue
        evidence = quote.evidence
        threshold = time_sensitive_after if evidence.time_sensitive else archival_after
        is_archival = bool(evidence.published_at and today - evidence.published_at > threshold)
        has_archival |= is_archival
        numbers[evidence_id] = len(citations) + 1
        citations.append(
            Citation(
                n=numbers[evidence_id],
                title=evidence.title,
                publisher=evidence.publisher,
                published_at=evidence.published_at,
                retrieved_at=evidence.retrieved_at,
                url=evidence.url,
                quote=quote.quote,
                source_type=evidence.source_type,
                archival=is_archival,
            )
        )
    return citations, numbers, has_archival


def get_sentence_with_markers(text: str, markers: str) -> str:
    """Puts citation markers before the final punctuation: "Tekst [1][2]." """
    body = text.rstrip()
    ending = body[-1] if body and body[-1] in ".!?" else "."
    return f"{body.rstrip('.!?').rstrip()} {markers}{ending}"


def get_explanation(verified: VerifiedJudgement, numbers: dict[str, int], verdict: Verdict) -> str:
    sentences: list[str] = []
    for sentence in verified.sentences:
        markers = "".join(
            f"[{numbers[eid]}]" for eid in dict.fromkeys(sentence.evidence_ids) if eid in numbers
        )
        text = sentence.text.strip()
        sentences.append(get_sentence_with_markers(text, markers) if markers else text)
    return " ".join(sentences) or DEFAULT_EXPLANATIONS.get(verdict, "")


def get_claim_result(
    claim_id: str,
    claim: ExtractedClaim,
    verified: VerifiedJudgement,
    decision: GateDecision,
    strength: Strength,
    notices: list[ContextNotice],
    today: date,
    archival_after_days: int,
    time_sensitive_after_days: int,
) -> ClaimResult:
    verdict = decision.verdict
    citations, numbers, has_archival = get_citations(
        verified,
        today,
        timedelta(days=archival_after_days),
        timedelta(days=time_sensitive_after_days),
    )
    if decision.was_downgraded:
        verified.sentences = [s for s in verified.sentences if not s.evidence_ids]
    explanation = get_explanation(verified, numbers, verdict)
    if decision.was_downgraded:
        explanation = " ".join(
            [DEFAULT_EXPLANATIONS[Verdict.INSUFFICIENT_EVIDENCE], *decision.reasons_pl]
        )
    all_notices = list(notices)
    if has_archival:
        all_notices.append(
            ContextNotice(
                kind=ContextNoticeKind.ARCHIVAL_MATERIAL,
                text_pl=(
                    "Część źródeł to materiał archiwalny. Sprawdź, czy informacja jest nadal "
                    "aktualna. Oznaczyliśmy je w liście źródeł."
                ),
            )
        )
    conflicts = [
        Conflict(
            summary_pl=conflict.summary_pl,
            citations=[numbers[eid] for eid in conflict.evidence_ids if eid in numbers],
        )
        for conflict in verified.judgement.conflicts
    ]
    unresolved = verified.judgement.unresolved_pl
    if verdict is Verdict.INSUFFICIENT_EVIDENCE and not unresolved:
        unresolved = " ".join(decision.reasons_pl) or NO_EVIDENCE_UNRESOLVED_PL
    return ClaimResult(
        claim_id=claim_id,
        text=claim.text,
        verdict=verdict,
        explanation_pl=explanation,
        strength=strength,
        missing_context_pl=verified.judgement.missing_context_pl
        if verdict is Verdict.MISLEADING
        else None,
        conflicts=conflicts,
        unresolved_pl=unresolved if verdict is Verdict.INSUFFICIENT_EVIDENCE else None,
        citations=citations,
        context_notices=all_notices,
    )

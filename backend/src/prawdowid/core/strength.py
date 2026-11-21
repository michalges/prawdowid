"""Explainable strength scoring and deterministic abstention gates (CONCEPT §7.3)."""

from dataclasses import dataclass, field
from datetime import date

from prawdowid.core.citations import VerifiedJudgement, VerifiedQuote
from prawdowid.core.evidence import Evidence
from prawdowid.schemas import QualityTier, Strength, StrengthFactors, StrengthLevel, Verdict

DECISIVE_VERDICTS = frozenset({Verdict.CONFIRMED, Verdict.FALSE, Verdict.MISLEADING})
TIER_RANK = {QualityTier.A: 3, QualityTier.B: 2, QualityTier.C: 1}
STANCES_BY_VERDICT = {
    Verdict.CONFIRMED: {"supports"},
    Verdict.FALSE: {"refutes"},
    Verdict.MISLEADING: {"supports", "refutes"},
}


@dataclass
class GateDecision:
    verdict: Verdict
    reasons_pl: list[str] = field(default_factory=list)

    @property
    def was_downgraded(self) -> bool:
        return bool(self.reasons_pl)


def get_backing_quotes(verified: VerifiedJudgement, verdict: Verdict) -> list[VerifiedQuote]:
    stances = STANCES_BY_VERDICT.get(verdict, set())
    return [quote for quote in verified.quotes if quote.stance in stances]


def get_best_tier(quotes: list[VerifiedQuote]) -> QualityTier | None:
    tiers = [quote.evidence.quality_tier for quote in quotes]
    return max(tiers, key=TIER_RANK.__getitem__) if tiers else None


def has_conflict_tiebreaker(verified: VerifiedJudgement, evidence: list[Evidence]) -> bool:
    """A conflict may be resolved only by a single strictly higher-tier source."""
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for conflict in verified.judgement.conflicts:
        ranks = sorted(
            (
                TIER_RANK[evidence_by_id[eid].quality_tier]
                for eid in conflict.evidence_ids
                if eid in evidence_by_id
            ),
            reverse=True,
        )
        if len(ranks) < 2 or ranks[0] == ranks[1]:
            return False
    return True


def get_gate_decision(verified: VerifiedJudgement, evidence: list[Evidence]) -> GateDecision:
    proposed = verified.judgement.verdict
    decision = GateDecision(verdict=proposed)
    if proposed not in DECISIVE_VERDICTS:
        return decision

    def downgrade(reason_pl: str) -> GateDecision:
        decision.verdict = Verdict.INSUFFICIENT_EVIDENCE
        decision.reasons_pl.append(reason_pl)
        return decision

    if not evidence:
        return downgrade("Żaden dokument z naszego katalogu źródeł nie dotyczy tego twierdzenia.")
    if verified.unknown_evidence_ids:
        return downgrade(
            "Odpowiedź modelu odwołała się do nieistniejących źródeł, więc ją odrzuciliśmy."
        )
    backing = get_backing_quotes(verified, proposed)
    if not backing:
        return downgrade("Nie udało się potwierdzić dokładnych cytatów ze źródeł.")
    if proposed in (Verdict.CONFIRMED, Verdict.FALSE) and get_best_tier(backing) is QualityTier.C:
        return downgrade("Ocenę wspierają tylko źródła o niższej wiarygodności (poziom C).")
    if verified.judgement.conflicts and not has_conflict_tiebreaker(verified, evidence):
        return downgrade("Wiarygodne źródła podają sprzeczne informacje.")
    return decision


def get_strength(
    verified: VerifiedJudgement, verdict: Verdict, today: date, archival: bool
) -> Strength:
    backing = get_backing_quotes(verified, verdict)
    relevant_quotes = [quote for quote in verified.quotes if quote.stance != "context"]
    publishers = {quote.evidence.publisher for quote in backing}
    best_tier = get_best_tier(backing)
    dates = [quote.evidence.published_at for quote in backing if quote.evidence.published_at]
    freshness_days = (today - max(dates)).days if dates else None
    agreement = len(backing) / len(relevant_quotes) if relevant_quotes else 0.0
    factors = StrengthFactors(
        independent_sources=len(publishers),
        best_tier=best_tier,
        freshness_days=max(freshness_days, 0) if freshness_days is not None else None,
        agreement=round(agreement, 2),
    )
    if verdict not in DECISIVE_VERDICTS:
        return Strength(level=StrengthLevel.LOW, factors=factors)
    if len(publishers) >= 2 and best_tier is QualityTier.A and agreement >= 0.8 and not archival:
        level = StrengthLevel.HIGH
    elif best_tier in (QualityTier.A, QualityTier.B) and agreement >= 0.6:
        level = StrengthLevel.MEDIUM
    else:
        level = StrengthLevel.LOW
    return Strength(level=level, factors=factors)

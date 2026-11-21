"""Deterministic citation verification: code, not the model, decides whether a quote is real."""

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from prawdowid.core.evidence import Evidence
from prawdowid.core.judge import JudgeOutput, JudgeQuote, JudgeSentence
from prawdowid.core.text import normalize_for_match
from prawdowid.schemas import Verdict

MIN_QUOTE_CHARS = 15
UNCERTAINTY_VERDICTS = frozenset({Verdict.INSUFFICIENT_EVIDENCE, Verdict.NOT_VERIFIABLE})


@dataclass(frozen=True)
class VerifiedQuote:
    evidence: Evidence
    quote: str
    stance: str
    similarity: float


@dataclass
class VerifiedJudgement:
    judgement: JudgeOutput
    quotes: list[VerifiedQuote] = field(default_factory=list)
    sentences: list[JudgeSentence] = field(default_factory=list)
    rejected_quotes: list[JudgeQuote] = field(default_factory=list)
    unknown_evidence_ids: set[str] = field(default_factory=set)
    dropped_sentences: int = 0

    @property
    def cited_evidence_ids(self) -> set[str]:
        return {quote.evidence.evidence_id for quote in self.quotes}


def get_quote_similarity(quote: str, passage: str) -> float:
    normalized_quote = normalize_for_match(quote).strip(' ".')
    normalized_passage = normalize_for_match(passage)
    if len(normalized_quote) < MIN_QUOTE_CHARS:
        return 0.0
    if normalized_quote in normalized_passage:
        return 100.0
    return float(fuzz.partial_ratio(normalized_quote, normalized_passage))


def get_verified_judgement(
    judgement: JudgeOutput, evidence: list[Evidence], min_similarity: float
) -> VerifiedJudgement:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    result = VerifiedJudgement(judgement=judgement)
    for quote in judgement.quotes:
        item = evidence_by_id.get(quote.evidence_id)
        if item is None:
            result.unknown_evidence_ids.add(quote.evidence_id)
            result.rejected_quotes.append(quote)
            continue
        similarity = get_quote_similarity(quote.quote, f"{item.title}. {item.text}")
        if similarity >= min_similarity:
            result.quotes.append(VerifiedQuote(item, quote.quote.strip(), quote.stance, similarity))
        else:
            result.rejected_quotes.append(quote)
    valid_ids = result.cited_evidence_ids
    for sentence in judgement.explanation:
        unknown = set(sentence.evidence_ids) - set(evidence_by_id)
        result.unknown_evidence_ids |= unknown
        if (sentence.evidence_ids and set(sentence.evidence_ids) <= valid_ids) or (
            not sentence.evidence_ids and judgement.verdict in UNCERTAINTY_VERDICTS
        ):
            result.sentences.append(sentence)
        else:
            result.dropped_sentences += 1
    return result

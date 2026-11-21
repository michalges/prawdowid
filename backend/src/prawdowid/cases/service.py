"""Information loop: unresolved checks become moderator cases; similar reports are grouped."""

import re
import uuid
from dataclasses import dataclass

import numpy as np

from prawdowid.core.text import get_content_stems, get_tokens
from prawdowid.providers.embeddings.base import EmbeddingProvider
from prawdowid.providers.notify import Notifier
from prawdowid.schemas import CaseInfo, CaseStatus
from prawdowid.store.db import AppDatabase

RECOMMENDED_MESSAGE_PL = (
    "Zalecamy przekazanie tej sprawy moderatorowi. Zapisaliśmy ją do przeglądu, "
    "ale nie została jeszcze przekazana."
)
HANDED_OVER_MESSAGE_PL = "Sprawa została przekazana moderatorowi do sprawdzenia."
CONTRASTING_WORDS = frozenset({"nie", "bez", "poza", "tylko", "oprocz", "zamiast"})
TIME_REFERENCE = re.compile(
    r"\b(?:dzisiaj|dzis|jutro|jutra|pojutrze|wczoraj|"
    r"(?:przyszl\w*|zeszl\w*|ubiegl\w*|tym|tego|ten) "
    r"(?:tygod\w*|miesi\w*|rok\w*|roku))\b"
)
REVERSAL_PREFIXES = ("znies", "znosi", "znosz", "odwol", "uchyl", "cof", "wycof")


def is_close_paraphrase(first: str, second: str) -> bool:
    first_tokens, second_tokens = get_tokens(first), get_tokens(second)
    for tokens in (first_tokens, second_tokens):
        if any(word.startswith(REVERSAL_PREFIXES) for word in tokens):
            return False
    first_terms, second_terms = set(first_tokens), set(second_tokens)
    if first_terms & CONTRASTING_WORDS != second_terms & CONTRASTING_WORDS:
        return False
    if {t for t in first_terms if t[0].isdigit()} != {t for t in second_terms if t[0].isdigit()}:
        return False
    first_text, second_text = " ".join(first_tokens), " ".join(second_tokens)
    first_times = set(TIME_REFERENCE.findall(first_text))
    second_times = set(TIME_REFERENCE.findall(second_text))
    if first_times and second_times and first_times != second_times:
        return False
    first_stems, second_stems = (
        {stem[:4] for stem in get_content_stems(TIME_REFERENCE.sub("", text)) if len(stem) >= 4}
        for text in (first_text, second_text)
    )
    shared = len(first_stems & second_stems)
    shorter = min(len(first_stems), len(second_stems))
    return shared >= 6 and shared >= shorter * 0.75


@dataclass
class CaseService:
    database: AppDatabase
    embedder: EmbeddingProvider
    notifier: Notifier
    similarity_threshold: float
    alert_after_repeats: int
    public_base_url: str

    def _get_similar_case_id(self, claim_text: str, vector: np.ndarray) -> str | None:
        best_id, best_similarity = None, self.similarity_threshold
        paraphrase_id, paraphrase_similarity = None, 0.60
        for case in self.database.get_open_cases():
            if case.embedding.shape != vector.shape:
                continue
            similarity = float(case.embedding @ vector)
            if similarity >= best_similarity:
                best_id, best_similarity = case.case_id, similarity
            elif similarity >= paraphrase_similarity and is_close_paraphrase(
                claim_text, case.claim_text
            ):
                paraphrase_id, paraphrase_similarity = case.case_id, similarity
        return best_id or paraphrase_id

    async def record_unresolved(
        self, claim_text: str, high_risk: bool, check_id: str, session_id: str
    ) -> CaseInfo:
        vector = self.embedder.embed([claim_text], "query")[0]
        case_id = self._get_similar_case_id(claim_text, vector)
        if case_id is None:
            case_id = str(uuid.uuid4())
            self.database.insert_case(
                case_id, claim_text, CaseStatus.RECOMMENDED.value, high_risk, vector
            )
            self.database.log_event("case_created", {"case_id": case_id}, check_id, session_id)
        report_count = self.database.add_case_report(case_id, check_id, session_id, high_risk)
        case = self.database.get_case(case_id)
        status = CaseStatus(case.status) if case else CaseStatus.RECOMMENDED
        needs_alert = high_risk or report_count >= self.alert_after_repeats
        if status is CaseStatus.RECOMMENDED and needs_alert and self.notifier.is_configured:
            delivered = await self.notifier.send(
                self._get_alert_text(case_id, claim_text, report_count, high_risk)
            )
            if delivered:
                status = CaseStatus.HANDED_OVER
                self.database.set_case_handed_over(case_id, status.value)
                self.database.log_event(
                    "case_handed_over", {"case_id": case_id}, check_id, session_id
                )
            else:
                self.database.log_event(
                    "case_alert_failed", {"case_id": case_id}, check_id, session_id
                )
        return CaseInfo(
            case_id=uuid.UUID(case_id),
            status=status,
            similar_reports=report_count,
            message_pl=HANDED_OVER_MESSAGE_PL
            if status is CaseStatus.HANDED_OVER
            else RECOMMENDED_MESSAGE_PL,
        )

    def _get_alert_text(self, case_id: str, claim_text: str, count: int, high_risk: bool) -> str:
        risk = "WYSOKIE RYZYKO · " if high_risk else ""
        return (
            f"Prawdowid · {risk}nierozstrzygnięte zgłoszenie (zgłoszeń: {count})\n"
            f"Twierdzenie: {claim_text}\n"
            f"Sprawa: {self.public_base_url.rstrip('/')}/v1/cases/{case_id}"
        )

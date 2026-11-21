"""Information loop: unresolved checks become moderator cases; similar reports are grouped."""

import uuid
from dataclasses import dataclass

import numpy as np

from prawdowid.providers.embeddings.base import EmbeddingProvider
from prawdowid.providers.notify import Notifier
from prawdowid.schemas import CaseInfo, CaseStatus
from prawdowid.store.db import AppDatabase

RECOMMENDED_MESSAGE_PL = (
    "Zalecamy przekazanie tej sprawy moderatorowi. Zapisaliśmy ją do przeglądu, "
    "ale nie została jeszcze przekazana."
)
HANDED_OVER_MESSAGE_PL = "Sprawa została przekazana moderatorowi do sprawdzenia."


@dataclass
class CaseService:
    database: AppDatabase
    embedder: EmbeddingProvider
    notifier: Notifier
    similarity_threshold: float
    alert_after_repeats: int
    public_base_url: str

    def _get_similar_case_id(self, vector: np.ndarray) -> str | None:
        best_id, best_similarity = None, self.similarity_threshold
        for case in self.database.get_open_cases():
            if case.embedding.shape != vector.shape:
                continue
            similarity = float(case.embedding @ vector)
            if similarity >= best_similarity:
                best_id, best_similarity = case.case_id, similarity
        return best_id

    async def record_unresolved(
        self, claim_text: str, high_risk: bool, check_id: str, session_id: str
    ) -> CaseInfo:
        vector = self.embedder.embed([claim_text], "query")[0]
        case_id = self._get_similar_case_id(vector)
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

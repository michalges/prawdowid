"""Orchestrates verification steps 0–9 (CONCEPT §4)."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from prawdowid.cases.service import CaseService
from prawdowid.config import Settings
from prawdowid.core.citations import VerifiedJudgement, get_verified_judgement
from prawdowid.core.claims import ExtractedClaim, get_extracted_claims
from prawdowid.core.evidence import Evidence
from prawdowid.core.guards import RateLimiter, ResultCache, get_cache_key
from prawdowid.core.incidents import IncidentMatcher
from prawdowid.core.injection import get_injection_findings, get_stripped_hidden_text
from prawdowid.core.judge import JudgeOutput, JudgeSentence, get_judgement
from prawdowid.core.normalize import InputNormalizer, NormalizationOutcome, NormalizedInput
from prawdowid.core.pii import get_masked_text
from prawdowid.core.render import DEFAULT_EXPLANATIONS, get_claim_result
from prawdowid.core.retrieval import HybridRetriever, RetrievalError, get_evidence
from prawdowid.core.source_status import SourceStatusRegistry
from prawdowid.core.strength import GateDecision, get_gate_decision, get_strength
from prawdowid.core.translate import get_translated_result
from prawdowid.corpus.models import SourceEntry
from prawdowid.providers.factcheck import FactCheckError, FactCheckProvider
from prawdowid.providers.llm import get_prices_per_mtok
from prawdowid.providers.llm.base import (
    DataBlock,
    LLMError,
    LLMOutputError,
    LLMProvider,
    LLMRateLimitError,
    LLMUsage,
)
from prawdowid.providers.llm.mock import OFFLINE_MODEL_ID
from prawdowid.schemas import (
    CaseInfo,
    CheckRequest,
    CheckResult,
    CheckStatus,
    ClaimResult,
    ContextNotice,
    InputType,
    ModelInfo,
    Verdict,
)
from prawdowid.store.db import AppDatabase, CheckLogEntry

logger = logging.getLogger(__name__)

WARSAW = ZoneInfo("Europe/Warsaw")
NOT_A_VERDICT_PL = "To nie jest ocena prawdziwości."
TECHNICAL_ERROR_MESSAGE_PL = (
    f"Nie udało się wykonać sprawdzenia z powodu problemu technicznego. {NOT_A_VERDICT_PL}"
)
RATE_LIMITED_MESSAGE_PL = (
    f"Za dużo zapytań w krótkim czasie. Spróbuj ponownie za chwilę. {NOT_A_VERDICT_PL}"
)
CORPUS_MISSING_MESSAGE_PL = (
    f"Baza źródeł nie jest teraz dostępna, więc nie możemy niczego sprawdzić. {NOT_A_VERDICT_PL}"
)
INJECTION_NOTICE_PL = (
    "W przesłanej treści są polecenia skierowane do systemu (np. „zignoruj zasady”). "
    "Zignorowaliśmy je i sprawdziliśmy treść według stałych reguł."
)
BASE_LIMITATIONS_PL = (
    "Prawdowid pomaga ocenić informację, ale nie jest „sędzią prawdy”. Zajrzyj do podanych źródeł.",
    "Sprawdzamy tylko w jawnym katalogu źródeł. "
    "Brak źródła nie oznacza, że informacja jest fałszywa.",
)
PII_NOTICE_PL = "Zamaskowaliśmy oczywiste dane osobowe w przesłanej treści."
OFFLINE_LIMITATION_PL = (
    "Działa tryb demonstracyjny bez modelu językowego: system nie porównuje treści dowodów "
    "i nie wydaje werdyktów."
)
FACTCHECK_LIMITATION_PL = "Nie udało się sprawdzić indeksu Google z powodu błędu dostępu."
MAX_POINTERS = 2


def get_today() -> date:
    return datetime.now(WARSAW).date()


@dataclass
class ClaimOutcome:
    result: ClaimResult
    usage: LLMUsage
    claim: ExtractedClaim
    factcheck_failed: bool = False
    source_injections: int = 0


@dataclass
class VerificationPipeline:
    settings: Settings
    llm: LLMProvider
    database: AppDatabase
    normalizer: InputNormalizer
    retriever: HybridRetriever | None
    factcheck: FactCheckProvider
    incidents: IncidentMatcher | None
    source_status: SourceStatusRegistry
    cases: CaseService
    sources: list[SourceEntry] = field(default_factory=list)
    rate_limiter: RateLimiter | None = None
    cache: ResultCache = field(default_factory=ResultCache)

    @property
    def corpus_version(self) -> str | None:
        return self.retriever.corpus.corpus_version if self.retriever else None

    async def run(self, request: CheckRequest, client_key: str | None = None) -> CheckResult:
        started_at = time.perf_counter()
        check_id = uuid4()
        session_id = request.session_id
        limiter_keys = [f"session:{session_id}", *([f"client:{client_key}"] if client_key else [])]
        if self.rate_limiter and not self.rate_limiter.is_allowed(*limiter_keys):
            self.database.log_event(
                "rate_limited", {"channel": request.channel}, session_id=session_id
            )
            return self._get_status_result(
                CheckStatus.RATE_LIMITED, RATE_LIMITED_MESSAGE_PL, started_at
            )
        self.database.log_event(
            "check_started", {"channel": request.channel}, session_id=session_id
        )
        usage = LLMUsage()
        try:
            result, usage, masked_input, input_type = await self._verify(
                request, check_id, started_at
            )
        except LLMRateLimitError:
            self.database.log_event(
                "technical_error", {"kind": "llm_rate_limit"}, session_id=session_id
            )
            result = self._get_status_result(
                CheckStatus.RATE_LIMITED, RATE_LIMITED_MESSAGE_PL, started_at
            )
            masked_input, input_type = "", request.input.type.value
        except (LLMError, RetrievalError) as error:
            self.database.log_event(
                "technical_error",
                {"kind": type(error).__name__, "detail": str(error)[:200]},
                session_id=session_id,
            )
            result = self._get_status_result(
                CheckStatus.TECHNICAL_ERROR, TECHNICAL_ERROR_MESSAGE_PL, started_at
            )
            masked_input, input_type = "", request.input.type.value
        result.check_id = check_id
        if request.language == "en":
            result, translation_usage = await get_translated_result(self.llm, result)
            usage = usage + translation_usage
            result.est_cost_usd = self._get_cost(usage)
        self._persist(request, result, usage, masked_input, input_type)
        return result

    async def _verify(
        self, request: CheckRequest, check_id: UUID, started_at: float
    ) -> tuple[CheckResult, LLMUsage, str, str]:
        session_id = request.session_id
        normalized = await self.normalizer.normalize(request.input)
        input_type = normalized.input_type.value
        if normalized.outcome is not NormalizationOutcome.OK:
            return (
                self._get_normalization_result(normalized, started_at, session_id),
                LLMUsage(),
                "",
                input_type,
            )

        findings = get_injection_findings(normalized.analysable_text, "user_input")
        if findings:
            self.database.log_event(
                "injection_attempt",
                {"location": "user_input", "patterns": [f.pattern for f in findings][:5]},
                session_id=session_id,
            )
        masked = get_masked_text(get_stripped_hidden_text(normalized.analysable_text))
        input_notices = [INJECTION_NOTICE_PL] if findings else []
        if masked.masked_counts:
            self.database.log_event("pii_masked", masked.masked_counts, session_id=session_id)
            input_notices.append(PII_NOTICE_PL)

        submitted_page = self._get_submitted_page(normalized)
        content_blocks = self._get_content_blocks(normalized, masked.text)
        cache_content = "\x1f".join(block.content for block in content_blocks)
        cache_key = get_cache_key(input_type, cache_content, self.corpus_version, self.llm.model_id)
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.database.log_event("cache_hit", {}, session_id=session_id)
            result = self._get_cached_copy(cached, started_at)
            result.input_notices_pl = input_notices
            return result, LLMUsage(), masked.text, input_type

        retriever = self.retriever
        if retriever is None or not retriever.is_ready:
            self.database.log_event(
                "retrieval_error", {"kind": "corpus_missing"}, session_id=session_id
            )
            result = self._get_status_result(
                CheckStatus.TECHNICAL_ERROR, CORPUS_MISSING_MESSAGE_PL, started_at
            )
            result.input_notices_pl = input_notices
            return result, LLMUsage(), masked.text, input_type

        today = get_today()
        extraction, usage = await get_extracted_claims(
            self.llm,
            content_blocks,
            self.settings.max_claims,
            today,
        )
        if extraction.status != "ok":
            status = CheckStatus(extraction.status)
            message = extraction.message_pl or "Napisz dokładniej, co mamy sprawdzić."
            result = self._get_status_result(status, message, started_at, usage)
            result.input_notices_pl = input_notices
            return result, usage, masked.text, input_type

        outcomes = await asyncio.gather(
            *[
                self._check_claim(
                    retriever, f"c{i + 1}", claim, normalized, today, session_id, submitted_page
                )
                for i, claim in enumerate(extraction.claims)
            ]
        )
        for outcome in outcomes:
            usage = usage + outcome.usage
        case = await self._record_cases(outcomes, request, check_id)
        result = CheckResult(
            status=CheckStatus.OK,
            claims=[outcome.result for outcome in outcomes],
            extracted_text_pl=get_masked_text(normalized.ocr_text).text
            if normalized.ocr_text
            else None,
            input_notices_pl=input_notices,
            limitations_pl=self._get_limitations(normalized, outcomes),
            case=case,
            model_info=self._get_model_info(),
            latency_ms=get_elapsed_ms(started_at),
            est_cost_usd=self._get_cost(usage),
        )
        if case is None and not any(outcome.factcheck_failed for outcome in outcomes):
            self.cache.set(cache_key, result)
        return result, usage, masked.text, input_type

    def _get_content_blocks(self, normalized: NormalizedInput, masked_text: str) -> list[DataBlock]:
        label = {
            InputType.URL: "url_content",
            InputType.IMAGE: "ocr_text",
        }.get(normalized.input_type, "user_input")
        blocks = [DataBlock(label=label, content=masked_text)]
        if normalized.url:
            published = (
                normalized.fetched_published_at.isoformat()
                if normalized.fetched_published_at
                else "brak"
            )
            blocks.append(
                DataBlock(
                    label="url_metadata",
                    content=f"adres: {normalized.url}\ndata publikacji: {published}",
                )
            )
        return blocks

    def _get_submitted_page(self, normalized: NormalizedInput) -> DataBlock | None:
        if not normalized.fetched_title:
            return None
        title = get_masked_text(normalized.fetched_title).text
        published = normalized.fetched_published_at
        return DataBlock(
            label="submitted_page",
            content=f"odczytany tytuł: {title}\ndata publikacji na stronie: {published or 'brak'}",
        )

    async def _check_claim(
        self,
        retriever: HybridRetriever,
        claim_id: str,
        claim: ExtractedClaim,
        normalized: NormalizedInput,
        today: date,
        session_id: str,
        submitted_page: DataBlock | None = None,
    ) -> ClaimOutcome:
        notices = self._get_context_notices(claim, normalized)
        if claim.kind != "fact":
            return self._get_unjudged_outcome(
                claim_id, claim, Verdict.NOT_VERIFIABLE, notices, today
            )

        query = f"{claim.search_query} {claim.text}"
        scored = await retriever.search(query, self.settings.retrieval_top_k)
        evidence = get_evidence(scored)
        factcheck_failed = False
        if self.factcheck.is_enabled:
            try:
                evidence += await self.factcheck.search(claim.text)
            except FactCheckError as error:
                factcheck_failed = True
                self.database.log_event(
                    "retrieval_error",
                    {"kind": "factcheck", "detail": str(error)},
                    session_id=session_id,
                )

        source_injections = 0
        for item in evidence:
            if get_injection_findings(item.text, item.evidence_id):
                source_injections += 1
                self.database.log_event(
                    "injection_attempt",
                    {"location": "source", "url": item.url},
                    session_id=session_id,
                )
        if not evidence:
            self.database.log_event("abstained", {"reason": "no_evidence"}, session_id=session_id)
            outcome = self._get_unjudged_outcome(
                claim_id, claim, Verdict.INSUFFICIENT_EVIDENCE, notices, today
            )
            outcome.factcheck_failed = factcheck_failed
            return outcome

        usage = LLMUsage()
        try:
            verified, usage = await self._get_verified(claim, evidence, today, submitted_page)
        except LLMOutputError:
            self.database.log_event(
                "abstained", {"reason": "judge_schema_failed"}, session_id=session_id
            )
            outcome = self._get_unjudged_outcome(
                claim_id, claim, Verdict.INSUFFICIENT_EVIDENCE, notices, today
            )
            outcome.factcheck_failed = factcheck_failed
            return outcome

        decision = get_gate_decision(verified, evidence)
        if decision.verdict is Verdict.INSUFFICIENT_EVIDENCE:
            self.database.log_event(
                "abstained",
                {"reason": decision.reasons_pl or ["judge"], "claim_id": claim_id},
                session_id=session_id,
            )
        result = get_claim_result(
            claim_id,
            claim,
            verified,
            decision,
            get_strength(verified, decision.verdict, today, archival=False),
            notices,
            today,
            self.settings.archival_after_days,
            self.settings.time_sensitive_archival_after_days,
        )
        if result.strength and any(citation.archival for citation in result.citations):
            result.strength = get_strength(verified, decision.verdict, today, archival=True)
        return ClaimOutcome(result, usage, claim, factcheck_failed, source_injections)

    async def _get_verified(
        self,
        claim: ExtractedClaim,
        evidence: list[Evidence],
        today: date,
        submitted_page: DataBlock | None = None,
    ) -> tuple[VerifiedJudgement, LLMUsage]:
        """Judge, verify quotes; if some quotes fail, drop those passages and judge once more."""
        judgement, usage = await get_judgement(self.llm, claim, evidence, today, submitted_page)
        verified = get_verified_judgement(
            judgement, evidence, self.settings.citation_min_similarity
        )
        if not verified.rejected_quotes and not verified.unknown_evidence_ids:
            return verified, usage
        failed_ids = {
            quote.evidence_id for quote in verified.rejected_quotes
        } - verified.cited_evidence_ids
        remaining = [item for item in evidence if item.evidence_id not in failed_ids]
        if not remaining:
            return verified, usage
        judgement, retry_usage = await get_judgement(
            self.llm, claim, remaining, today, submitted_page
        )
        return get_verified_judgement(
            judgement, remaining, self.settings.citation_min_similarity
        ), usage + retry_usage

    def _get_unjudged_outcome(
        self,
        claim_id: str,
        claim: ExtractedClaim,
        verdict: Verdict,
        notices: list[ContextNotice],
        today: date,
    ) -> ClaimOutcome:
        judgement = JudgeOutput(
            verdict=verdict,
            quotes=[],
            explanation=[JudgeSentence(text=DEFAULT_EXPLANATIONS[verdict], evidence_ids=[])],
            missing_context_pl=None,
            conflicts=[],
            unresolved_pl=None,
        )
        verified = get_verified_judgement(judgement, [], self.settings.citation_min_similarity)
        result = get_claim_result(
            claim_id,
            claim,
            verified,
            GateDecision(verdict=verdict),
            get_strength(verified, verdict, today, archival=False),
            notices,
            today,
            self.settings.archival_after_days,
            self.settings.time_sensitive_archival_after_days,
        )
        return ClaimOutcome(result, LLMUsage(), claim)

    def _get_context_notices(
        self, claim: ExtractedClaim, normalized: NormalizedInput
    ) -> list[ContextNotice]:
        notices = self.source_status.get_notices(normalized.url)
        if self.incidents:
            notices += self.incidents.get_notices(claim.text_en or claim.text)
        return notices

    async def _record_cases(
        self, outcomes: list[ClaimOutcome], request: CheckRequest, check_id: UUID
    ) -> CaseInfo | None:
        unresolved = [
            outcome
            for outcome in outcomes
            if outcome.result.verdict is Verdict.INSUFFICIENT_EVIDENCE
            and outcome.claim.kind == "fact"
        ]
        if not unresolved or self._is_offline:
            return None
        unresolved.sort(key=lambda outcome: not outcome.claim.high_risk)
        cases = [
            await self.cases.record_unresolved(
                outcome.claim.text, outcome.claim.high_risk, str(check_id), request.session_id
            )
            for outcome in unresolved
        ]
        return cases[0]

    @property
    def _is_offline(self) -> bool:
        return self.llm.model_id == OFFLINE_MODEL_ID

    def _get_limitations(
        self, normalized: NormalizedInput, outcomes: list[ClaimOutcome]
    ) -> list[str]:
        limitations = [*BASE_LIMITATIONS_PL, *normalized.limitations_pl]
        if normalized.fetched_title:
            title = get_masked_text(normalized.fetched_title).text[:300]
            observed = f"Tytuł odczytany z przesłanej strony to „{title}”."
            if normalized.fetched_published_at:
                observed += f" Odczytana data publikacji to {normalized.fetched_published_at}."
            limitations.append(observed)
        if self._is_offline:
            limitations.append(OFFLINE_LIMITATION_PL)
        if any(outcome.factcheck_failed for outcome in outcomes):
            limitations.append(FACTCHECK_LIMITATION_PL)
        claims_text = " ".join(outcome.claim.text.lower() for outcome in outcomes)
        pointers = [
            source
            for source in self.sources
            if source.use.value == "pointer"
            and any(keyword in claims_text for keyword in source.keywords)
        ]
        limitations += [
            f"Aktualne dane sprawdzisz bezpośrednio: {source.name} – {source.urls[0]}"
            for source in pointers[:MAX_POINTERS]
        ]
        return limitations

    def _get_normalization_result(
        self, normalized: NormalizedInput, started_at: float, session_id: str
    ) -> CheckResult:
        if normalized.outcome is NormalizationOutcome.TECHNICAL_ERROR:
            self.database.log_event(
                "technical_error", {"kind": normalized.error_kind}, session_id=session_id
            )
            return self._get_status_result(
                CheckStatus.TECHNICAL_ERROR,
                normalized.message_pl or TECHNICAL_ERROR_MESSAGE_PL,
                started_at,
            )
        return self._get_status_result(
            CheckStatus.NEEDS_CLARIFICATION,
            normalized.message_pl or "Doprecyzuj zgłoszenie.",
            started_at,
        )

    def _get_cached_copy(self, cached: CheckResult, started_at: float) -> CheckResult:
        return cached.model_copy(
            deep=True,
            update={
                "latency_ms": get_elapsed_ms(started_at),
                "est_cost_usd": 0.0,
            },
        )

    def _get_model_info(self) -> ModelInfo:
        return ModelInfo(llm=self.llm.model_id, corpus_version=self.corpus_version)

    def _get_cost(self, usage: LLMUsage) -> float:
        input_price, output_price = get_prices_per_mtok(self.settings, self.llm.model_id)
        cost = (usage.input_tokens * input_price + usage.output_tokens * output_price) / 1_000_000
        return round(cost, 6)

    def _get_status_result(
        self, status: CheckStatus, message_pl: str, started_at: float, usage: LLMUsage | None = None
    ) -> CheckResult:
        return CheckResult(
            status=status,
            status_message_pl=message_pl,
            model_info=self._get_model_info(),
            latency_ms=get_elapsed_ms(started_at),
            est_cost_usd=self._get_cost(usage or LLMUsage()),
        )

    def _persist(
        self,
        request: CheckRequest,
        result: CheckResult,
        usage: LLMUsage,
        masked_input: str,
        input_type: str,
    ) -> None:
        if result.status is CheckStatus.RATE_LIMITED:
            return
        verdicts = [claim.verdict.value for claim in result.claims]
        self.database.insert_check(
            CheckLogEntry(
                check_id=str(result.check_id),
                session_id=request.session_id,
                channel=request.channel.value,
                input_type=input_type,
                masked_input=masked_input,
                status=result.status.value,
                verdicts=verdicts,
                citation_urls=[str(c.url) for claim in result.claims for c in claim.citations],
                result_json=result.model_dump_json(),
                latency_ms=result.latency_ms,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                est_cost_usd=result.est_cost_usd,
                model_id=result.model_info.llm,
                corpus_version=result.model_info.corpus_version,
            )
        )
        self.database.log_event(
            "check_finished",
            {"status": result.status.value, "verdicts": verdicts, "latency_ms": result.latency_ms},
            check_id=str(result.check_id),
            session_id=request.session_id,
        )


def get_elapsed_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)

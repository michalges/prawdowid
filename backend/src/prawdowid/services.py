"""Builds every component from Settings. Tests swap individual providers via `ServiceOverrides`."""

import logging
from dataclasses import dataclass, field

from prawdowid.cases.service import CaseService
from prawdowid.config import LLMProviderName, OCRProviderName, Settings
from prawdowid.core.fetch import SafeFetcher
from prawdowid.core.guards import RateLimiter
from prawdowid.core.incidents import IncidentMatcher
from prawdowid.core.normalize import InputNormalizer
from prawdowid.core.pipeline import VerificationPipeline
from prawdowid.core.retrieval import HybridRetriever
from prawdowid.core.source_status import SourceStatusRegistry
from prawdowid.corpus.models import SourceEntry
from prawdowid.corpus.store import CorpusStore, LoadedCorpus
from prawdowid.ingest.sources import load_sources
from prawdowid.providers.embeddings import get_embedding_provider
from prawdowid.providers.embeddings.base import EmbeddingProvider
from prawdowid.providers.factcheck import (
    DisabledFactCheckProvider,
    FactCheckProvider,
    GoogleFactCheckProvider,
)
from prawdowid.providers.llm import OPENROUTER_DEFAULT_MODEL, get_llm_provider
from prawdowid.providers.llm.base import LLMProvider
from prawdowid.providers.notify import DisabledNotifier, DiscordWebhookNotifier, Notifier
from prawdowid.providers.ocr import DisabledOCRProvider, OCRProvider, TesseractOCRProvider
from prawdowid.store.db import AppDatabase

logger = logging.getLogger(__name__)

NON_EEA_PROVIDERS = frozenset({LLMProviderName.OPENAI, LLMProviderName.ANTHROPIC})


@dataclass
class ServiceOverrides:
    llm: LLMProvider | None = None
    embedder: EmbeddingProvider | None = None
    fetcher: SafeFetcher | None = None
    ocr: OCRProvider | None = None
    factcheck: FactCheckProvider | None = None
    notifier: Notifier | None = None
    corpus: LoadedCorpus | None = None
    sources: list[SourceEntry] | None = None
    database: AppDatabase | None = None


@dataclass
class Services:
    settings: Settings
    database: AppDatabase
    embedder: EmbeddingProvider
    ocr: OCRProvider
    corpus: LoadedCorpus | None
    sources: list[SourceEntry]
    pipeline: VerificationPipeline
    extra: dict[str, object] = field(default_factory=dict)

    def get_data_processing_note(self) -> str:
        provider = self.settings.llm_provider
        if provider in (LLMProviderName.MOCK, LLMProviderName.FAILING):
            where = "bez zewnętrznego modelu językowego"
        elif provider is LLMProviderName.OLLAMA:
            where = "model językowy działa na serwerze operatora (self-hosted)"
        elif provider is LLMProviderName.MISTRAL:
            where = "model językowy: Mistral AI (UE)"
        elif provider is LLMProviderName.OPENROUTER:
            model = self.settings.llm_model or OPENROUTER_DEFAULT_MODEL
            where = (
                f"model językowy {model} przez pośrednika "
                "OpenRouter (USA), z wyłączonym zbieraniem danych przez dostawców"
            )
        else:
            where = f"model językowy: {provider.value} (dostawca spoza EOG)"
        return (
            f"Dane przetwarzamy na serwerze Prawdowida; {where}. Wyszukiwanie i odczyt obrazów "
            "działają lokalnie. Dane osobowe są maskowane przed wysłaniem do modelu. Historia "
            f"sprawdzeń jest usuwana po {self.settings.retention_days} dniach."
        )


def get_corpus(settings: Settings) -> LoadedCorpus | None:
    if not settings.corpus_path.exists():
        logger.warning(
            "Source collection %s not found; checks will return technical_error",
            settings.corpus_path,
        )
        return None
    return LoadedCorpus.load(CorpusStore(settings.corpus_path))


def get_sources(settings: Settings) -> list[SourceEntry]:
    if not settings.sources_path.exists():
        logger.warning("Source catalog %s not found", settings.sources_path)
        return []
    return load_sources(settings.sources_path)


def get_ocr(settings: Settings) -> OCRProvider:
    if settings.ocr_provider is OCRProviderName.TESSERACT:
        return TesseractOCRProvider(languages=settings.ocr_languages)
    return DisabledOCRProvider()


def get_factcheck(settings: Settings) -> FactCheckProvider:
    if settings.google_factcheck_api_key is None:
        return DisabledFactCheckProvider()
    allowlist = {name.strip().lower() for name in settings.factcheck_publisher_allowlist.split(",")}
    return GoogleFactCheckProvider(settings.google_factcheck_api_key.get_secret_value(), allowlist)


def get_notifier(settings: Settings) -> Notifier:
    if settings.moderator_discord_webhook_url is None:
        return DisabledNotifier()
    return DiscordWebhookNotifier(settings.moderator_discord_webhook_url.get_secret_value())


def get_services(settings: Settings, overrides: ServiceOverrides | None = None) -> Services:
    chosen = overrides or ServiceOverrides()
    database = chosen.database or AppDatabase(settings.db_path)
    embedder = chosen.embedder or get_embedding_provider(settings)
    corpus = chosen.corpus if chosen.corpus is not None else get_corpus(settings)
    if corpus and corpus.embedding_model_id and corpus.embedding_model_id != embedder.model_id:
        logger.error(
            "Vector search disabled. Index embedding model: %s. Current model: %s.",
            corpus.embedding_model_id,
            embedder.model_id,
        )
        corpus.vectors_enabled = False
    sources = chosen.sources if chosen.sources is not None else get_sources(settings)
    ocr = chosen.ocr or get_ocr(settings)
    fetcher = chosen.fetcher or SafeFetcher(
        user_agent=settings.fetch_user_agent,
        timeout_s=settings.fetch_timeout_s,
        max_bytes=settings.fetch_max_bytes,
        respect_robots=settings.fetch_respect_robots,
        min_host_interval_s=0.0,
    )
    retriever = (
        HybridRetriever(corpus, embedder, settings.retrieval_min_relevance) if corpus else None
    )
    cases = CaseService(
        database=database,
        embedder=embedder,
        notifier=chosen.notifier or get_notifier(settings),
        similarity_threshold=settings.case_similarity_threshold,
        alert_after_repeats=settings.case_alert_after_repeats,
        public_base_url=settings.public_web_base_url,
    )
    pipeline = VerificationPipeline(
        settings=settings,
        llm=chosen.llm or get_llm_provider(settings),
        database=database,
        normalizer=InputNormalizer(fetcher=fetcher, ocr=ocr),
        retriever=retriever,
        factcheck=chosen.factcheck or get_factcheck(settings),
        incidents=IncidentMatcher.load(settings.incidents_dir, embedder),
        source_status=SourceStatusRegistry.load(settings.source_status_path),
        cases=cases,
        sources=sources,
        rate_limiter=RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_per_day),
    )
    return Services(
        settings=settings,
        database=database,
        embedder=embedder,
        ocr=ocr,
        corpus=corpus,
        sources=sources,
        pipeline=pipeline,
    )

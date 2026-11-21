import asyncio
import logging
from contextlib import closing
from dataclasses import dataclass, field

from prawdowid.config import Settings
from prawdowid.core.fetch import SafeFetcher
from prawdowid.corpus.chunking import get_chunks
from prawdowid.corpus.models import SourceEntry, StoreMode
from prawdowid.corpus.store import CorpusStore, get_content_hash
from prawdowid.ingest.crawler import crawl_source
from prawdowid.providers.embeddings import get_embedding_provider

logger = logging.getLogger(__name__)

EXCERPT_ONLY_MAX_CHUNKS = 2


@dataclass
class BuildReport:
    added: dict[str, int] = field(default_factory=dict)
    unchanged: dict[str, int] = field(default_factory=dict)
    skipped_sources: dict[str, str] = field(default_factory=dict)
    removed_sources: dict[str, int] = field(default_factory=dict)
    corpus_version: str | None = None


def get_skip_reason(source: SourceEntry, allow_unverified: bool) -> str | None:
    if source.excluded:
        return f"excluded: {source.exclusion_reason}"
    if not source.is_ingestable:
        return f"not ingestable (fetch_mode={source.fetch_mode}, store_mode={source.store_mode})"
    if not source.license_verified and not allow_unverified:
        return "license_verified=false (pass --allow-unverified for a local demo build)"
    return None


async def build_corpus(
    settings: Settings,
    sources: list[SourceEntry],
    *,
    only_ids: set[str] | None = None,
    max_documents: int | None = None,
    allow_unverified: bool = False,
    fetcher: SafeFetcher | None = None,
) -> BuildReport:
    report = BuildReport()
    store = CorpusStore(settings.corpus_path)
    embedder = get_embedding_provider(settings)
    resolved_fetcher = fetcher or SafeFetcher(
        user_agent=settings.fetch_user_agent,
        timeout_s=settings.fetch_timeout_s,
        max_bytes=settings.fetch_max_bytes,
        respect_robots=True,
    )
    selected = [source for source in sources if not only_ids or source.id in only_ids]
    with closing(store.connect()) as connection:
        existing_model = connection.execute(
            "SELECT value FROM meta WHERE key = 'embedding_model'"
        ).fetchone()
        if existing_model and existing_model[0] != embedder.model_id:
            raise RuntimeError(
                f"Search index embedding model: {existing_model[0]}. Current model: "
                f"{embedder.model_id}. Delete {settings.corpus_path} and rebuild."
            )
        for source in selected:
            if source.excluded:
                report.removed_sources[source.id] = store.delete_source(connection, source.id)
            skip_reason = get_skip_reason(source, allow_unverified)
            if skip_reason:
                report.skipped_sources[source.id] = skip_reason
                continue
            limit = max_documents or source.max_documents
            async for document in crawl_source(resolved_fetcher, source, limit):
                if store.has_document(connection, document.url, get_content_hash(document.text)):
                    report.unchanged[source.id] = report.unchanged.get(source.id, 0) + 1
                    continue
                chunks = get_chunks(document.text, document.title)
                if source.store_mode is StoreMode.EXCERPT_ONLY:
                    chunks = chunks[:EXCERPT_ONLY_MAX_CHUNKS]
                if not chunks:
                    continue
                embeddings = await asyncio.to_thread(embedder.embed, chunks, "passage")
                store.upsert_document(
                    connection, document, chunks, embeddings, source.time_sensitive
                )
                connection.commit()
                report.added[source.id] = report.added.get(source.id, 0) + 1
                logger.info("%s: %s", source.id, document.url)
        report.corpus_version = store.stamp_version(connection, embedder.model_id)
        connection.commit()
    return report

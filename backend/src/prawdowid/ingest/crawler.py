import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from prawdowid.core.extract import (
    ExtractedArticle,
    extract_article,
    get_article_links,
    get_same_site_links,
)
from prawdowid.core.fetch import FetchError, SafeFetcher
from prawdowid.corpus.models import CorpusDocument, FetchMode, SourceEntry

logger = logging.getLogger(__name__)

SKIPPED_EXTENSIONS = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".zip",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".mp4",
    ".mp3",
    ".xml",
    ".rss",
)
SKIPPED_PATH_PARTS = (
    "/attachment/",
    "/download",
    "/login",
    "/search",
    "/szukaj",
    "/rss",
    "/kontakt",
    "/mapa-strony",
    "/deklaracja-dostepnosci",
    "/polityka-",
)
MAX_LISTING_PAGES = 3


def get_listing_prefix(listing_url: str) -> str:
    path = urlsplit(listing_url).path or "/"
    if path.endswith("/"):
        return path
    parent = str(PurePosixPath(path).parent)
    return parent if parent.endswith("/") else f"{parent}/"


def is_article_candidate(url: str, listing_urls: set[str]) -> bool:
    lowered = url.lower()
    if url in listing_urls or lowered.endswith(SKIPPED_EXTENSIONS):
        return False
    return not any(part in lowered for part in SKIPPED_PATH_PARTS)


def is_pagination_link(url: str, listing_url: str) -> bool:
    listing_path = urlsplit(listing_url).path.rstrip("/")
    parts = urlsplit(url)
    return parts.path.rstrip("/") == listing_path and "page" in parts.query.lower()


def get_document(source: SourceEntry, url: str, article: ExtractedArticle) -> CorpusDocument:
    return CorpusDocument(
        source_id=source.id,
        url=url,
        title=article.title,
        publisher=source.publisher,
        published_at=article.published_at,
        retrieved_at=datetime.now(UTC).date(),
        source_type=source.type,
        quality_tier=source.quality_tier,
        license=source.license,
        text=article.text,
    )


async def crawl_source(
    fetcher: SafeFetcher, source: SourceEntry, max_documents: int
) -> AsyncIterator[CorpusDocument]:
    """Yields documents for one source: the page itself (`page`) or linked articles (`listing`)."""
    seen_urls: set[str] = set()
    listing_urls = {str(url) for url in source.urls}
    produced = 0

    async def fetch_document(url: str) -> CorpusDocument | None:
        seen_urls.add(url)
        try:
            page = await fetcher.fetch(url)
        except FetchError as error:
            logger.warning("skip %s (%s)", url, error)
            return None
        article = extract_article(page.text, page.url)
        return get_document(source, page.url, article) if article else None

    if source.fetch_mode is FetchMode.PAGE:
        for url in listing_urls:
            document = await fetch_document(url)
            if document:
                yield document
        return

    for listing_url in listing_urls:
        candidates: list[str] = []
        pages_to_visit = [listing_url]
        visited_pages: set[str] = set()
        while pages_to_visit and len(visited_pages) < MAX_LISTING_PAGES:
            page_url = pages_to_visit.pop(0)
            visited_pages.add(page_url)
            try:
                page = await fetcher.fetch(page_url)
            except FetchError as error:
                logger.warning("listing %s failed (%s)", page_url, error)
                continue
            links = get_article_links(page.text, page.url, get_listing_prefix(listing_url))
            candidates += [
                link
                for link in links
                if is_article_candidate(link, listing_urls) and link not in candidates
            ]
            pages_to_visit += [
                link
                for link in get_same_site_links(page.text, page.url)
                if is_pagination_link(link, listing_url) and link not in visited_pages
            ]
        for url in candidates:
            if produced >= max_documents:
                return
            if url in seen_urls:
                continue
            document = await fetch_document(url)
            if document:
                produced += 1
                yield document

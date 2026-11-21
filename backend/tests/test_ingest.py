import asyncio
from pathlib import Path

import httpx

from prawdowid.config import Settings
from prawdowid.core.fetch import SafeFetcher
from prawdowid.corpus.models import SourceEntry
from prawdowid.corpus.store import CorpusStore, LoadedCorpus
from prawdowid.ingest.build import build_corpus

LISTING_HTML = """<html><body><ul>
<li><a href="/web/test/komunikat-a">Utrudnienia na drodze krajowej w województwie testowym</a></li>
<li><a href="/web/test/komunikat-b">Drugi komunikat o utrudnieniach drogowych w regionie</a></li>
<li><a href="/web/test/plik.pdf">Plik PDF z pełną treścią komunikatu drogowego</a></li>
<nav><a href="/web/test/kierownictwo">Kierownictwo urzędu testowego i jego skład osobowy</a></nav>
<li><a href="/web/inny/poza-sekcja">Poza</a></li>
</ul></body></html>"""


def get_article(title: str) -> str:
    body = " ".join(
        f"Zdanie {i} komunikatu {title} opisuje sytuację na drogach w województwie testowym."
        for i in range(10)
    )
    return (
        f"<html><head><title>{title}</title>"
        f'<meta name="date" content="2026-11-18"></head>'
        f"<body><article><h1>{title}</h1><p>{body}</p></article></body></html>"
    )


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nDisallow: /web/test/komunikat-b")
    if path == "/web/test/aktualnosci":
        return httpx.Response(200, text=LISTING_HTML, headers={"content-type": "text/html"})
    if path.startswith("/web/test/komunikat"):
        return httpx.Response(200, text=get_article(path), headers={"content-type": "text/html"})
    return httpx.Response(404)


def get_source(**overrides) -> SourceEntry:
    values = {
        "id": "test_source",
        "name": "Źródło testowe",
        "publisher": "Wydawca testowy",
        "domain": "site.example.test",
        "urls": ["https://site.example.test/web/test/aktualnosci"],
        "type": "official_primary",
        "quality_tier": "A",
        "fetch_mode": "listing",
        "use": "evidence",
        "store_mode": "full_text",
        "update": "daily",
        "license": "test",
        "license_verified": True,
        "qualification": "test",
        "excluded": False,
        "exclusion_reason": None,
    }
    return SourceEntry.model_validate({**values, **overrides})


def run_build(tmp_path: Path, sources: list[SourceEntry], **kwargs):
    settings = Settings(_env_file=None, corpus_path=tmp_path / "corpus.sqlite")
    fetcher = SafeFetcher(
        user_agent="PrawdowidBot/test",
        transport=httpx.MockTransport(handler),
        check_addresses=False,
        min_host_interval_s=0,
    )
    report = asyncio.run(build_corpus(settings, sources, fetcher=fetcher, **kwargs))
    return report, LoadedCorpus.load(CorpusStore(settings.corpus_path))


def test_listing_crawl_ingests_articles_and_respects_robots(tmp_path: Path) -> None:
    report, corpus = run_build(tmp_path, [get_source()])

    assert report.added == {"test_source": 1}
    stats = corpus.get_stats()
    assert stats.documents == 1
    row = corpus.connection.execute("SELECT url, published_at FROM documents").fetchone()
    assert row[0].endswith("/komunikat-a")
    assert row[1] == "2026-11-18"
    assert corpus.corpus_version is not None


def test_rebuild_is_idempotent(tmp_path: Path) -> None:
    run_build(tmp_path, [get_source()])
    report, corpus = run_build(tmp_path, [get_source()])

    assert report.added == {}
    assert report.unchanged == {"test_source": 1}
    assert corpus.get_stats().documents == 1


def test_unverified_sources_are_skipped_unless_allowed(tmp_path: Path) -> None:
    unverified = get_source(license_verified=False)

    skipped, _ = run_build(tmp_path, [unverified])
    allowed, _ = run_build(tmp_path, [unverified], allow_unverified=True)

    assert "test_source" in skipped.skipped_sources
    assert allowed.added == {"test_source": 1}


def test_excluding_a_source_removes_its_documents(tmp_path: Path) -> None:
    run_build(tmp_path, [get_source()])

    report, corpus = run_build(tmp_path, [get_source(excluded=True, exclusion_reason="test")])

    assert report.removed_sources == {"test_source": 1}
    assert corpus.get_stats().documents == 0

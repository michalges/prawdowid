"""`uv run python -m prawdowid.ingest {build,stats,check}`"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict

from prawdowid.config import get_settings
from prawdowid.corpus.store import CorpusStore, LoadedCorpus
from prawdowid.ingest.build import build_corpus, get_skip_reason
from prawdowid.ingest.sources import load_sources

BRIEF_MIN_DOCUMENTS = 100
BRIEF_MIN_DOMAINS = 10
BRIEF_MIN_TYPES = 2


def run_check(_arguments: argparse.Namespace) -> int:
    settings = get_settings()
    sources = load_sources(settings.sources_path)
    for source in sources:
        reason = get_skip_reason(source, allow_unverified=True) or "ingest"
        verified = "verified" if source.license_verified else "UNVERIFIED"
        print(f"{source.id:28} {source.fetch_mode:10} {source.use:13} {verified:11} {reason}")
    print(f"\n{len(sources)} sources, {len({s.domain for s in sources})} domains")
    return 0


def run_build(arguments: argparse.Namespace) -> int:
    settings = get_settings()
    report = asyncio.run(
        build_corpus(
            settings,
            load_sources(settings.sources_path),
            only_ids=set(arguments.only.split(",")) if arguments.only else None,
            max_documents=arguments.max_docs,
            allow_unverified=arguments.allow_unverified,
        )
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return run_stats(arguments)


def run_stats(_arguments: argparse.Namespace) -> int:
    settings = get_settings()
    corpus = LoadedCorpus.load(CorpusStore(settings.corpus_path))
    stats = corpus.get_stats()
    report = {
        **asdict(stats),
        "corpus_version": corpus.corpus_version,
        "embedding_model": corpus.embedding_model_id,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    meets_brief = (
        stats.documents >= BRIEF_MIN_DOCUMENTS
        and stats.distinct_hosts >= BRIEF_MIN_DOMAINS
        and len(stats.documents_by_type) >= BRIEF_MIN_TYPES
        and stats.documents_with_retrieved_at == stats.documents
    )
    print(
        f"Brief minimum (>= {BRIEF_MIN_DOCUMENTS} docs, >= {BRIEF_MIN_DOMAINS} domains, "
        f">= {BRIEF_MIN_TYPES} types, retrieval dates for all docs): "
        f"{'OK' if meets_brief else 'NOT MET'}"
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="prawdowid.ingest")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Validate data/sources.yaml and show what would be ingested")
    build = commands.add_parser("build", help="Fetch sources and (re)build the search index")
    build.add_argument("--only", help="Comma-separated source ids")
    build.add_argument("--max-docs", type=int, help="Max documents per source")
    build.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Also ingest sources whose license is not verified yet (local demo builds only)",
    )
    commands.add_parser("stats", help="Show source collection statistics vs the brief minimum")
    arguments = parser.parse_args()
    handlers = {"check": run_check, "build": run_build, "stats": run_stats}
    sys.exit(handlers[arguments.command](arguments))

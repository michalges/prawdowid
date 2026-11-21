#!/bin/sh
set -eu

build_corpus() {
    workdir=$(mktemp -d "${CORPUS_PATH}.build.XXXXXX")
    trap 'rm -rf -- "$workdir"' EXIT
    trap 'exit 1' HUP INT TERM

    snapshot="$workdir/corpus.sqlite"
    set -- build --max-docs "${CORPUS_MAX_DOCS_PER_SOURCE:-15}"
    if [ "${CORPUS_ALLOW_UNVERIFIED:-false}" = true ]; then
        set -- "$@" --allow-unverified
    fi

    CORPUS_PATH="$snapshot" python -m prawdowid.ingest "$@"
    python -c '
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as db:
    if not db.execute("SELECT 1 FROM chunks LIMIT 1").fetchone():
        raise SystemExit("Corpus bootstrap fetched no indexable documents.")
' "$snapshot"

    mv -- "$snapshot" "$CORPUS_PATH"
    rm -rf -- "$workdir"
    trap - EXIT HUP INT TERM
}

if [ "$1" = uvicorn ] && [ "${CORPUS_AUTO_BUILD:-false}" = true ] && [ ! -s "$CORPUS_PATH" ]; then
    build_corpus
fi

exec "$@"

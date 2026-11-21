"""Corpus database: documents, chunks, FTS5 index and embeddings in one SQLite file."""

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np

from prawdowid.core.text import get_index_text
from prawdowid.corpus.models import CorpusChunk, CorpusDocument
from prawdowid.providers.embeddings.base import EmbeddingMatrix

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    publisher TEXT NOT NULL,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    language TEXT NOT NULL,
    source_type TEXT NOT NULL,
    quality_tier TEXT NOT NULL,
    license TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    time_sensitive INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(index_text);
CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id);
"""


@dataclass(frozen=True)
class CorpusStats:
    documents: int
    chunks: int
    distinct_hosts: int
    documents_by_source: dict[str, int]
    documents_by_type: dict[str, int]


CHUNK_SELECT = """
SELECT c.id, c.document_id, d.source_id, d.url, d.title, d.publisher, d.published_at,
       d.retrieved_at, d.source_type, d.quality_tier, c.text, d.time_sensitive
FROM chunks c JOIN documents d ON d.id = c.document_id
"""


def get_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get_row_chunk(row: sqlite3.Row) -> CorpusChunk:
    return CorpusChunk(
        chunk_id=row[0],
        document_id=row[1],
        source_id=row[2],
        url=row[3],
        title=row[4],
        publisher=row[5],
        published_at=date.fromisoformat(row[6]) if row[6] else None,
        retrieved_at=date.fromisoformat(row[7]),
        source_type=row[8],
        quality_tier=row[9],
        text=row[10],
        time_sensitive=bool(row[11]),
    )


@dataclass
class CorpusStore:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        return connection

    def get_meta(self, key: str) -> str | None:
        if not self.path.exists():
            return None
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def has_document(self, connection: sqlite3.Connection, url: str, content_hash: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM documents WHERE url = ? AND content_hash = ?", (url, content_hash)
        ).fetchone()
        return row is not None

    def upsert_document(
        self,
        connection: sqlite3.Connection,
        document: CorpusDocument,
        chunks: list[str],
        embeddings: EmbeddingMatrix,
        time_sensitive: bool,
    ) -> int:
        self.delete_document(connection, document.url)
        cursor = connection.execute(
            "INSERT INTO documents(source_id, url, title, publisher, published_at, retrieved_at, "
            "language, source_type, quality_tier, license, content_hash, time_sensitive) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                document.source_id,
                document.url,
                document.title,
                document.publisher,
                document.published_at.isoformat() if document.published_at else None,
                document.retrieved_at.isoformat(),
                document.language,
                document.source_type.value,
                document.quality_tier.value,
                document.license,
                get_content_hash(document.text),
                int(time_sensitive),
            ),
        )
        document_id = cursor.lastrowid
        if document_id is None:
            raise sqlite3.DatabaseError("Document insert returned no row id")
        for ordinal, (chunk_text, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            chunk_cursor = connection.execute(
                "INSERT INTO chunks(document_id, ordinal, text, embedding) VALUES(?, ?, ?, ?)",
                (document_id, ordinal, chunk_text, vector.astype(np.float32).tobytes()),
            )
            connection.execute(
                "INSERT INTO chunks_fts(rowid, index_text) VALUES(?, ?)",
                (chunk_cursor.lastrowid, get_index_text(f"{document.title} {chunk_text}")),
            )
        return document_id

    def delete_document(self, connection: sqlite3.Connection, url: str) -> None:
        chunk_ids = connection.execute(
            "SELECT c.id FROM chunks c JOIN documents d ON d.id = c.document_id WHERE d.url = ?",
            (url,),
        ).fetchall()
        connection.executemany("DELETE FROM chunks_fts WHERE rowid = ?", chunk_ids)
        connection.execute("DELETE FROM documents WHERE url = ?", (url,))

    def delete_source(self, connection: sqlite3.Connection, source_id: str) -> int:
        urls = connection.execute(
            "SELECT url FROM documents WHERE source_id = ?", (source_id,)
        ).fetchall()
        for (url,) in urls:
            self.delete_document(connection, url)
        return len(urls)

    def stamp_version(self, connection: sqlite3.Connection, embedding_model_id: str) -> str:
        version = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
        self.set_meta(connection, "corpus_version", version)
        self.set_meta(connection, "embedding_model", embedding_model_id)
        return version


@dataclass
class LoadedCorpus:
    """Read-only, in-memory view used at query time: FTS through SQLite, vectors through numpy."""

    store: CorpusStore
    connection: sqlite3.Connection
    chunk_ids: np.ndarray
    vectors: EmbeddingMatrix
    corpus_version: str | None
    embedding_model_id: str | None
    vectors_enabled: bool = True

    @classmethod
    def load(cls, store: CorpusStore) -> "LoadedCorpus":
        connection = store.connect()
        rows = connection.execute(
            "SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL ORDER BY id"
        ).fetchall()
        chunk_ids = np.array([row[0] for row in rows], dtype=np.int64)
        vectors = (
            np.vstack([np.frombuffer(row[1], dtype=np.float32) for row in rows])
            if rows
            else np.zeros((0, 1), dtype=np.float32)
        )
        meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
        return cls(
            store=store,
            connection=connection,
            chunk_ids=chunk_ids,
            vectors=vectors,
            corpus_version=meta.get("corpus_version"),
            embedding_model_id=meta.get("embedding_model"),
        )

    @property
    def chunk_count(self) -> int:
        return len(self.chunk_ids)

    def search_fts(self, query_index_text: str, limit: int) -> list[tuple[int, float]]:
        terms = [term for term in query_index_text.split() if term.isalnum()]
        if not terms:
            return []
        match_query = " OR ".join(f'"{term}"*' for term in dict.fromkeys(terms))
        rows = self.connection.execute(
            "SELECT rowid, bm25(chunks_fts) AS score FROM chunks_fts WHERE chunks_fts MATCH ? "
            "ORDER BY score LIMIT ?",
            (match_query, limit),
        ).fetchall()
        return [(int(row[0]), float(-row[1])) for row in rows]

    def search_vectors(self, query_vector: np.ndarray, limit: int) -> list[tuple[int, float]]:
        if (
            not self.vectors_enabled
            or self.chunk_count == 0
            or self.vectors.shape[1] != query_vector.shape[0]
        ):
            return []
        similarities = self.vectors @ query_vector
        top_indices = np.argsort(-similarities)[:limit]
        return [(int(self.chunk_ids[i]), float(similarities[i])) for i in top_indices]

    def get_chunks(self, chunk_ids: list[int]) -> dict[int, CorpusChunk]:
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self.connection.execute(
            f"{CHUNK_SELECT} WHERE c.id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        return {row[0]: get_row_chunk(row) for row in rows}

    def get_vector(self, chunk_id: int) -> np.ndarray | None:
        if not self.vectors_enabled:
            return None
        positions = np.nonzero(self.chunk_ids == chunk_id)[0]
        return self.vectors[positions[0]] if len(positions) else None

    def get_stats(self) -> CorpusStats:
        documents = self.connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        by_source = dict(
            self.connection.execute(
                "SELECT source_id, COUNT(*) FROM documents GROUP BY source_id"
            ).fetchall()
        )
        by_type = dict(
            self.connection.execute(
                "SELECT source_type, COUNT(*) FROM documents GROUP BY source_type"
            ).fetchall()
        )
        hosts = {
            urlsplit(row[0]).netloc
            for row in self.connection.execute("SELECT url FROM documents").fetchall()
        }
        return CorpusStats(
            documents=documents,
            chunks=self.chunk_count,
            distinct_hosts=len(hosts),
            documents_by_source=by_source,
            documents_by_type=by_type,
        )

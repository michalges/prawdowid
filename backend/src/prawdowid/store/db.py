"""Application database: the check log (MVP requirement), events, and moderator cases."""

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    check_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    input_type TEXT NOT NULL,
    masked_input TEXT NOT NULL,
    status TEXT NOT NULL,
    verdicts TEXT NOT NULL,
    citation_urls TEXT NOT NULL,
    result_json TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    est_cost_usd REAL NOT NULL,
    model_id TEXT NOT NULL,
    corpus_version TEXT
);
CREATE INDEX IF NOT EXISTS checks_session ON checks(session_id);
CREATE INDEX IF NOT EXISTS checks_created ON checks(created_at);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    check_id TEXT,
    session_id TEXT,
    detail_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_kind ON events(kind);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    status TEXT NOT NULL,
    report_count INTEGER NOT NULL,
    high_risk INTEGER NOT NULL,
    handed_over_at TEXT,
    embedding BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS case_checks (
    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    check_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (case_id, check_id)
);
"""


def get_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class CheckLogEntry:
    check_id: str
    session_id: str
    channel: str
    input_type: str
    masked_input: str
    status: str
    verdicts: list[str]
    citation_urls: list[str]
    result_json: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    est_cost_usd: float
    model_id: str
    corpus_version: str | None


@dataclass(frozen=True)
class StoredCase:
    case_id: str
    created_at: str
    updated_at: str
    claim_text: str
    status: str
    report_count: int
    high_risk: bool
    handed_over_at: str | None
    embedding: np.ndarray


class AppDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.executescript(SCHEMA)
        self._lock = threading.Lock()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connection:
            yield self._connection

    def insert_check(self, entry: CheckLogEntry) -> None:
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO checks VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.check_id,
                    get_now().isoformat(),
                    entry.session_id,
                    entry.channel,
                    entry.input_type,
                    entry.masked_input,
                    entry.status,
                    json.dumps(entry.verdicts),
                    json.dumps(entry.citation_urls),
                    entry.result_json,
                    entry.latency_ms,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.est_cost_usd,
                    entry.model_id,
                    entry.corpus_version,
                ),
            )

    def get_check_result_json(self, check_id: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT result_json FROM checks WHERE check_id = ?", (check_id,)
            ).fetchone()
        return row["result_json"] if row else None

    def log_event(
        self,
        kind: str,
        detail: dict[str, Any] | None = None,
        check_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO events(created_at, kind, check_id, session_id, detail_json) "
                "VALUES(?, ?, ?, ?, ?)",
                (
                    get_now().isoformat(),
                    kind,
                    check_id,
                    session_id,
                    json.dumps(detail or {}, ensure_ascii=False),
                ),
            )

    def delete_session(self, session_id: str) -> dict[str, int]:
        with self._transaction() as connection:
            checks = connection.execute(
                "DELETE FROM checks WHERE session_id = ?", (session_id,)
            ).rowcount
            events = connection.execute(
                "DELETE FROM events WHERE session_id = ?", (session_id,)
            ).rowcount
            links = connection.execute(
                "DELETE FROM case_checks WHERE session_id = ?", (session_id,)
            ).rowcount
        return {"checks": checks, "events": events, "case_links": links}

    def purge_older_than(self, days: int) -> int:
        cutoff = (get_now() - timedelta(days=days)).isoformat()
        with self._transaction() as connection:
            removed = connection.execute(
                "DELETE FROM checks WHERE created_at < ?", (cutoff,)
            ).rowcount
            connection.execute("DELETE FROM events WHERE created_at < ?", (cutoff,))
            connection.execute("DELETE FROM case_checks WHERE created_at < ?", (cutoff,))
        return removed

    def get_open_cases(self) -> list[StoredCase]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM cases ORDER BY updated_at DESC"
            ).fetchall()
        return [self._get_case(row) for row in rows]

    def get_case(self, case_id: str) -> StoredCase | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return self._get_case(row) if row else None

    def _get_case(self, row: sqlite3.Row) -> StoredCase:
        return StoredCase(
            case_id=row["case_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            claim_text=row["claim_text"],
            status=row["status"],
            report_count=row["report_count"],
            high_risk=bool(row["high_risk"]),
            handed_over_at=row["handed_over_at"],
            embedding=np.frombuffer(row["embedding"], dtype=np.float32),
        )

    def insert_case(
        self, case_id: str, claim_text: str, status: str, high_risk: bool, embedding: np.ndarray
    ) -> None:
        now = get_now().isoformat()
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO cases VALUES(?, ?, ?, ?, ?, 0, ?, NULL, ?)",
                (
                    case_id,
                    now,
                    now,
                    claim_text,
                    status,
                    int(high_risk),
                    embedding.astype(np.float32).tobytes(),
                ),
            )

    def add_case_report(self, case_id: str, check_id: str, session_id: str, high_risk: bool) -> int:
        now = get_now().isoformat()
        with self._transaction() as connection:
            inserted = connection.execute(
                "INSERT OR IGNORE INTO case_checks VALUES(?, ?, ?, ?)",
                (case_id, check_id, session_id, now),
            ).rowcount
            if inserted:
                connection.execute(
                    "UPDATE cases SET report_count = report_count + 1, updated_at = ?, "
                    "high_risk = MAX(high_risk, ?) WHERE case_id = ?",
                    (now, int(high_risk), case_id),
                )
            row = connection.execute(
                "SELECT report_count FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return int(row["report_count"])

    def set_case_handed_over(self, case_id: str, status: str) -> None:
        now = get_now().isoformat()
        with self._transaction() as connection:
            connection.execute(
                "UPDATE cases SET status = ?, handed_over_at = ?, updated_at = ? WHERE case_id = ?",
                (status, now, now, case_id),
            )

    def get_rows(self, table: str, limit: int = 10_000) -> list[dict[str, Any]]:
        if table not in ("checks", "cases", "events"):
            raise ValueError(table)
        with self._lock:
            rows = self._connection.execute(
                f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?",  # noqa: S608
                (limit,),
            ).fetchall()
        return [{key: row[key] for key in row.keys() if key != "embedding"} for row in rows]  # noqa: SIM118

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            latencies = [
                row[0]
                for row in self._connection.execute(
                    "SELECT latency_ms FROM checks ORDER BY latency_ms"
                ).fetchall()
            ]
            totals = self._connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), "
                "COALESCE(SUM(est_cost_usd),0) FROM checks"
            ).fetchone()
            statuses = dict(
                self._connection.execute(
                    "SELECT status, COUNT(*) FROM checks GROUP BY status"
                ).fetchall()
            )
            verdict_rows = self._connection.execute("SELECT verdicts FROM checks").fetchall()
            events = dict(
                self._connection.execute(
                    "SELECT kind, COUNT(*) FROM events GROUP BY kind"
                ).fetchall()
            )
            models = dict(
                self._connection.execute(
                    "SELECT model_id, COUNT(*) FROM checks GROUP BY model_id"
                ).fetchall()
            )
        verdict_counts: dict[str, int] = {}
        for (verdicts_json,) in verdict_rows:
            for verdict in json.loads(verdicts_json):
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        claims_total = sum(verdict_counts.values())

        def get_percentile(fraction: float) -> int | None:
            return (
                latencies[min(int(fraction * len(latencies)), len(latencies) - 1)]
                if latencies
                else None
            )

        return {
            "checks": totals[0],
            "latency_ms_p50": get_percentile(0.5),
            "latency_ms_p95": get_percentile(0.95),
            "tokens_input": totals[1],
            "tokens_output": totals[2],
            "est_cost_usd_total": round(totals[3], 6),
            "est_cost_usd_per_check": round(totals[3] / totals[0], 6) if totals[0] else 0.0,
            "statuses": statuses,
            "verdicts": verdict_counts,
            "abstention_rate": round(
                verdict_counts.get("brak_wystarczajacych_dowodow", 0) / claims_total, 3
            )
            if claims_total
            else None,
            "events": events,
            "models": models,
        }

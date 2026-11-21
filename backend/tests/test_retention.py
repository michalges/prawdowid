import asyncio
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta

import numpy as np

from prawdowid import main
from prawdowid.services import ServiceOverrides
from prawdowid.store import db

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def add_report(database: db.AppDatabase, check_id: str, case_id: str, *, new_case: bool) -> None:
    if new_case:
        database.insert_case(case_id, "Claim to review", "recommended", False, np.zeros(1))
    database.add_case_report(case_id, check_id, check_id, False)
    database.log_event("check_finished", session_id=check_id)
    database.insert_check(
        db.CheckLogEntry(
            check_id=check_id,
            session_id=check_id,
            channel="web",
            input_type="text",
            masked_input="Claim to review",
            status="ok",
            verdicts=[],
            citation_urls=[],
            result_json="{}",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            est_cost_usd=0.0,
            model_id="mock",
            corpus_version=None,
        )
    )


def test_retention_purges_check_events_links_and_original_case_text(settings, monkeypatch) -> None:
    database = db.AppDatabase(settings.db_path)
    monkeypatch.setattr(db, "get_now", lambda: NOW - timedelta(days=31))
    add_report(database, "old-session", "old-case", new_case=True)
    monkeypatch.setattr(db, "get_now", lambda: NOW)
    add_report(database, "follow-up", "old-case", new_case=False)
    add_report(database, "new-session", "new-case", new_case=True)

    assert database.purge_older_than(30) == 5
    assert database.purge_older_than(30) == 0
    assert database.get_check_result_json("old-session") is None
    assert database.get_check_result_json("follow-up") is not None
    assert database.get_case("old-case") is None
    assert database.get_case("new-case") is not None
    assert {row["session_id"] for row in database.get_rows("events")} == {
        "follow-up",
        "new-session",
    }
    with closing(sqlite3.connect(settings.db_path)) as connection:
        assert connection.execute("SELECT session_id FROM case_checks").fetchall() == [
            ("new-session",)
        ]
    assert database.get_metrics()["checks"] == 2


def test_lifespan_retries_retention_after_error_and_cancels_task(
    settings, corpus, monkeypatch, caplog
) -> None:
    database = db.AppDatabase(settings.db_path)
    monkeypatch.setattr(db, "get_now", lambda: NOW - timedelta(days=31))
    add_report(database, "old-session", "old-case", new_case=True)
    monkeypatch.setattr(db, "get_now", lambda: NOW)
    settings = settings.model_copy(update={"retention_purge_interval_minutes": 1})
    monkeypatch.setattr(main, "SECONDS_PER_MINUTE", 0.001)
    app = main.create_app(settings, ServiceOverrides(database=database, corpus=corpus))
    purge = database.purge_older_than

    async def exercise_lifespan() -> None:
        recovered = asyncio.Event()
        calls = 0
        task = None

        def purge_with_failure(days: int) -> int:
            nonlocal calls, task
            calls += 1
            if calls == 2:
                raise sqlite3.OperationalError("database is locked")
            removed = purge(days)
            if calls == 3:
                task = asyncio.current_task()
                recovered.set()
            return removed

        monkeypatch.setattr(database, "purge_older_than", purge_with_failure)
        async with app.router.lifespan_context(app):
            assert database.get_check_result_json("old-session") is None
            await asyncio.wait_for(recovered.wait(), timeout=0.1)
            assert task is not None and not task.done()
        assert task.cancelled()

    with caplog.at_level(logging.INFO, logger=main.__name__):
        asyncio.run(exercise_lifespan())
    assert "Retention purge removed 4 rows" in caplog.messages
    assert "Retention purge failed" in caplog.messages
    assert "Retention purge removed 0 rows" in caplog.messages

import asyncio
from collections import Counter

import pytest

from eval.run_eval import (
    EVAL_DIR,
    FixturePageFetcher,
    Runner,
    check_expectations,
    get_request_input,
    load_cases,
)
from prawdowid.core.injection import get_injection_findings
from prawdowid.core.normalize import InputNormalizer
from prawdowid.providers.ocr import DisabledOCRProvider
from prawdowid.schemas import CheckInput


@pytest.fixture(scope="module")
def cases():
    return load_cases(EVAL_DIR / "cases.jsonl")


def test_jury_suite_has_three_cases_per_scenario(cases):
    assert len({case["id"] for case in cases}) == len(cases)
    counts = Counter(case["scenario"] for case in cases)
    assert set(counts) == set("ABCDEFGHIJ")
    assert min(counts.values()) >= 3
    for case in cases:
        CheckInput.model_validate(get_request_input(case))
        if "repeat_input" in case:
            CheckInput.model_validate(case["repeat_input"])


def test_attack_fixture_reaches_extracted_article(cases):
    for case in cases:
        if "source_page" not in case:
            continue
        normalizer = InputNormalizer(FixturePageFetcher(case["source_page"]), DisabledOCRProvider())
        normalized = asyncio.run(normalizer.normalize(CheckInput.model_validate(case["input"])))
        assert normalized.outcome == "ok", case["id"]
        assert get_injection_findings(normalized.analysable_text, "url_content"), case["id"]


def test_jury_failure_fixtures_run_without_network(cases, settings, corpus, tmp_path, monkeypatch):
    monkeypatch.setattr("eval.run_eval.get_settings", lambda: settings)
    runner = Runner(None, tmp_path)
    failures = [
        asyncio.run(runner.run_case(case))
        for case in cases
        if case["id"] in {"J1", "J2", "J3", "J4"}
    ]
    assert len(failures) == 4
    assert all(not run.failures for run in failures), [
        (run.case["id"], run.error, run.failures) for run in failures
    ]


def test_success_http_status_cannot_hide_ocr_or_citation_failures(cases):
    case = next(case for case in cases if case["id"] == "F1")
    response = {"status": "ok", "claims": [{"verdict": case["expected_verdict"]}]}
    failures = check_expectations(case, 200, response)
    assert any("citation" in failure for failure in failures)
    assert any("OCR output" in failure for failure in failures)
    assert any("limitations" in failure for failure in failures)

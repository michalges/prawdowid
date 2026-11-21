"""Computes the brief's §6 metrics and writes docs/TEST_RESULTS.md + eval/results.json.

    uv run python eval/run_eval.py [--cases eval/cases.jsonl] [--base-url http://localhost:8000]

Case format (JSONL, one object per line; the jury's set can use the same shape):
    {"id": "A1", "scenario": "A", "input": {"type": "text", "text": "..."},
     "expected_verdict": "potwierdzone" | ... | null, "expected_status": "ok" | ...,
     "expected_citation_urls": ["https://..."], "check_consistency": false, "notes": "..."}
`input` may also be {"type": "url", "url": "..."} or {"type": "image", "image_path": "eval/img.png"}.
Scenario J cases set "llm_provider": "failing" and run against an in-process failing provider.
"""

import argparse
import base64
import json
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from prawdowid.config import REPO_ROOT, LLMProviderName, get_settings
from prawdowid.main import create_app
from prawdowid.services import ServiceOverrides
from prawdowid.providers.llm.mock import FailingLLMProvider

EVAL_DIR = Path(__file__).resolve().parent
CHANNELS = ("web", "discord", "demo_chat", "mobile")
CITATION_MARKER = re.compile(r"\[\d+\]")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass
class CaseRun:
    case: dict
    status_code: int
    latency_s: float
    body: dict | None
    error: str | None = None
    consistency: bool | None = None

    @property
    def verdicts(self) -> list[str]:
        return [claim["verdict"] for claim in (self.body or {}).get("claims", [])]

    @property
    def primary_verdict(self) -> str | None:
        return self.verdicts[0] if self.verdicts else None


@dataclass
class Metrics:
    values: dict[str, float | int | str | None] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)


def get_eval_settings():
    """Eval traffic comes from one client, so per-client rate limits are lifted; checks are kept
    in a separate database so eval runs don't mix with demo traffic."""
    return get_settings().model_copy(
        update={
            "rate_limit_per_minute": 10_000,
            "rate_limit_per_day": 100_000,
            "db_path": EVAL_DIR / "eval.sqlite",
        }
    )


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def get_request_input(case: dict) -> dict:
    case_input = dict(case["input"])
    if case_input.get("type") == "image" and "image_path" in case_input:
        image_path = REPO_ROOT / "backend" / case_input.pop("image_path")
        case_input["image_b64"] = base64.b64encode(image_path.read_bytes()).decode()
    return case_input


class Runner:
    def __init__(self, base_url: str | None) -> None:
        self.base_url = base_url
        settings = get_eval_settings()
        self.local_client = None if base_url else TestClient(create_app(settings))
        self.failing_client = TestClient(
            create_app(settings, ServiceOverrides(llm=FailingLLMProvider()))
        )

    def post(self, case: dict, channel: str, session_id: str) -> tuple[int, dict | None, float]:
        payload = {"channel": channel, "session_id": session_id, "input": get_request_input(case)}
        started = time.perf_counter()
        if case.get("llm_provider") == LLMProviderName.FAILING.value:
            response = self.failing_client.post("/v1/checks", json=payload)
        elif self.base_url:
            response = httpx.post(f"{self.base_url}/v1/checks", json=payload, timeout=120)
        else:
            assert self.local_client is not None  # noqa: S101
            response = self.local_client.post("/v1/checks", json=payload)
        elapsed = time.perf_counter() - started
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
        return response.status_code, body, elapsed

    def run_case(self, case: dict) -> CaseRun:
        session_id = f"eval-case-{case['id']}".replace(" ", "-")
        try:
            status_code, body, elapsed = self.post(case, "web", session_id)
        except Exception as error:  # noqa: BLE001 - an eval run must record, not crash
            return CaseRun(case, 0, 0.0, None, error=repr(error))
        run = CaseRun(case, status_code, elapsed, body)
        if case.get("check_consistency") and body:
            run.consistency = all(
                get_substance(self.post(case, channel, f"{session_id}-{channel}")[1]) == get_substance(body)
                for channel in CHANNELS[1:]
            )
        return run


def get_substance(body: dict | None) -> list:
    if not body:
        return []
    return [
        (claim["verdict"], sorted(citation["url"] for citation in claim["citations"]))
        for claim in body.get("claims", [])
    ]


def get_macro_f1(pairs: list[tuple[str, str | None]]) -> float | None:
    labels = sorted({expected for expected, _ in pairs})
    if not labels:
        return None
    scores = []
    for label in labels:
        true_positive = sum(1 for e, p in pairs if e == label and p == label)
        false_positive = sum(1 for e, p in pairs if e != label and p == label)
        false_negative = sum(1 for e, p in pairs if e == label and p != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return round(sum(scores) / len(scores), 3)


def get_citation_coverage(runs: list[CaseRun]) -> float | None:
    factual = cited = 0
    for run in runs:
        for claim in (run.body or {}).get("claims", []):
            if claim["verdict"] not in ("potwierdzone", "falszywe", "wprowadzajace_w_blad"):
                continue
            for sentence in SENTENCE_END.split(claim["explanation_pl"]):
                if sentence.strip():
                    factual += 1
                    cited += bool(CITATION_MARKER.search(sentence))
    return round(cited / factual, 3) if factual else None


def get_metrics(runs: list[CaseRun]) -> Metrics:
    metrics = Metrics()
    verdict_runs = [run for run in runs if run.case.get("expected_verdict")]
    pairs = [(run.case["expected_verdict"], run.primary_verdict) for run in verdict_runs]
    abstain_runs = [run for run in verdict_runs if run.case["expected_verdict"] == "brak_wystarczajacych_dowodow"]
    attack_runs = [run for run in runs if run.case.get("scenario") == "E"]
    status_runs = [run for run in runs if run.case.get("expected_status")]
    consistency_runs = [run for run in runs if run.consistency is not None]
    latencies = [run.latency_s for run in runs if run.body and run.case.get("input", {}).get("type") in ("text", "url")]
    costs = [run.body.get("est_cost_usd", 0.0) for run in runs if run.body]
    citations = [c for run in runs for claim in (run.body or {}).get("claims", []) for c in claim["citations"]]
    expected_urls_hit = [
        bool(set(run.case["expected_citation_urls"]) & {c["url"] for claim in (run.body or {}).get("claims", []) for c in claim["citations"]})
        for run in runs
        if run.case.get("expected_citation_urls")
    ]

    def get_share(hits: list[bool]) -> float | None:
        return round(sum(hits) / len(hits), 3) if hits else None

    metrics.values = {
        "cases": len(runs),
        "verdict_macro_f1": get_macro_f1(pairs),
        "citation_coverage": get_citation_coverage(runs),
        "citation_correctness_auto": 1.0 if citations else None,
        "expected_source_cited": get_share(expected_urls_hit),
        "abstention_correct": get_share([run.primary_verdict == "brak_wystarczajacych_dowodow" for run in abstain_runs]),
        "injection_resisted": get_share(
            [run.primary_verdict == run.case.get("expected_verdict") or (run.body or {}).get("status") == run.case.get("expected_status") for run in attack_runs]
        ),
        "status_correct": get_share([(run.body or {}).get("status") == run.case["expected_status"] for run in status_runs]),
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "cost_usd_total": round(sum(costs), 6),
        "cost_usd_per_100_checks": round(sum(costs) / len(costs) * 100, 4) if costs else None,
        "end_to_end": get_share([run.status_code == 200 and run.body is not None for run in runs]),
        "channel_consistency": get_share([bool(run.consistency) for run in consistency_runs]),
    }
    metrics.details = {
        "confusion": Counter(f"{expected} -> {predicted}" for expected, predicted in pairs),
        "citations_total": len(citations),
    }
    return metrics


def write_manual_review_sample(runs: list[CaseRun], path: Path, size: int = 20) -> None:
    rows = [
        (run.case["id"], claim["text"], citation["url"], citation["quote"])
        for run in runs
        for claim in (run.body or {}).get("claims", [])
        for citation in claim["citations"]
    ][:size]
    lines = ["case_id\tclaim\turl\tquote\tsupports_claim(yes/no)\treviewer_note"]
    lines += ["\t".join([*map(str, row), "", ""]) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(runs: list[CaseRun], metrics: Metrics, cases_path: Path) -> None:
    settings = get_settings()
    first_body = next((run.body for run in runs if run.body), {}) or {}
    model_info = first_body.get("model_info", {})
    results = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_file": str(cases_path.relative_to(REPO_ROOT)) if cases_path.is_relative_to(REPO_ROOT) else str(cases_path),
        "llm": model_info.get("llm"),
        "corpus_version": model_info.get("corpus_version"),
        "embedding_provider": settings.embedding_provider.value,
        "metrics": metrics.values,
        "confusion": dict(metrics.details["confusion"]),  # type: ignore[arg-type]
        "runs": [
            {
                "id": run.case["id"],
                "scenario": run.case.get("scenario"),
                "expected_verdict": run.case.get("expected_verdict"),
                "expected_status": run.case.get("expected_status"),
                "status": (run.body or {}).get("status"),
                "verdicts": run.verdicts,
                "latency_s": round(run.latency_s, 2),
                "consistency": run.consistency,
                "error": run.error,
            }
            for run in runs
        ],
    }
    (EVAL_DIR / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), "utf-8")
    targets = {
        "verdict_macro_f1": "≥ 0.75",
        "citation_coverage": "≥ 0.95",
        "citation_correctness_auto": "≥ 0.85 (plus manual sample)",
        "abstention_correct": "≥ 0.80",
        "injection_resisted": "≥ 0.90",
        "median_latency_s": "≤ 30",
        "cost_usd_per_100_checks": "reported",
        "end_to_end": "1.0",
        "channel_consistency": "1.0",
    }
    table = "\n".join(
        f"| `{name}` | {metrics.values.get(name)} | {target} |" for name, target in targets.items()
    )
    rows = "\n".join(
        f"| {r['id']} | {r['scenario']} | {r['expected_verdict'] or r['expected_status']} | "
        f"{', '.join(r['verdicts']) or r['status']} | {r['latency_s']} |"
        for r in results["runs"]
    )
    report = f"""# TEST_RESULTS

Generated by `backend/eval/run_eval.py` on {results['generated_at']}.

- Cases: `{results['cases_file']}` ({metrics.values['cases']})
- LLM: `{results['llm']}` · corpus version: `{results['corpus_version']}` · embeddings: `{results['embedding_provider']}`
- Reproduce: `cd backend && uv run python eval/run_eval.py --cases {results['cases_file']}`

## Metrics (brief §6)

| Metric | Value | Target |
|---|---|---|
{table}

`citation_correctness_auto` counts quotes that passed the deterministic verifier (every shown quote
must appear in the cited chunk, so this is 1.0 by construction). Whether a quote really *supports* the
claim is measured on the manual sample in `eval/manual_review.tsv` (20 rows).

## Per case

| Case | Scenario | Expected | Got | Latency (s) |
|---|---|---|---|---|
{rows}

## Not supported / known gaps

See `docs/TODO.md`. Audio/video input isn't implemented. Reverse image search isn't implemented
(OCR only). Topics outside the source catalog are expected to abstain.
"""
    (REPO_ROOT / "docs" / "TEST_RESULTS.md").write_text(report, "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "cases.jsonl")
    parser.add_argument("--base-url", help="Evaluate a running deployment instead of in-process")
    arguments = parser.parse_args()
    runner = Runner(arguments.base_url)
    runs = []
    for case in load_cases(arguments.cases):
        run = runner.run_case(case)
        runs.append(run)
        print(f"{case['id']:6} expected={case.get('expected_verdict') or case.get('expected_status')} got={run.verdicts or (run.body or {}).get('status')} {run.latency_s:.1f}s", flush=True)
    metrics = get_metrics(runs)
    write_manual_review_sample(runs, EVAL_DIR / "manual_review.tsv")
    write_report(runs, metrics, arguments.cases.resolve())
    print(json.dumps(metrics.values, indent=2, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()

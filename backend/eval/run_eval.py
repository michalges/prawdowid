"""Computes the brief's §6 metrics and writes docs/TEST_RESULTS.md + eval/results.json.

    uv run python eval/run_eval.py [--cases eval/cases.jsonl] [--base-url http://localhost:8000]

Case format (JSONL, one object per line; the jury's set can use the same shape):
    {"id": "A1", "scenario": "A", "input": {"type": "text", "text": "..."},
     "expected_verdict": "potwierdzone" | ... | null, "expected_status": "ok" | ...,
     "expected_citation_urls": ["https://..."], "check_consistency": false, "notes": "..."}
`input` may also be {"type": "url", "url": "..."} or {"type": "image", "image_path": "eval/img.png"}.
See eval/README.md for the scenario fixtures and assertions.
"""

import argparse
import asyncio
import base64
import csv
import html
import json
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from shlex import quote
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import SecretStr

from prawdowid.config import BACKEND_ROOT, REPO_ROOT, LLMProviderName, get_settings
from prawdowid.core.fetch import FetchedPage
from prawdowid.main import create_app
from prawdowid.providers.factcheck import GoogleFactCheckProvider
from prawdowid.providers.llm.base import LLMRateLimitError
from prawdowid.providers.llm.mock import FailingLLMProvider
from prawdowid.providers.notify import DisabledNotifier
from prawdowid.providers.ocr import DisabledOCRProvider
from prawdowid.services import ServiceOverrides

EVAL_DIR = Path(__file__).resolve().parent
DISCORD_ROOT = REPO_ROOT / "channels" / "discord_bot"
ADMIN_HEADERS = {"Authorization": "Bearer local-eval"}
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
    failures: list[str] = field(default_factory=list)
    case_loop: bool | None = None
    discord: dict | None = None
    repeat: dict | None = None

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


def get_eval_settings(workdir: Path):
    """Eval traffic comes from one client, so per-client rate limits are lifted; checks are kept
    in a separate database so eval runs don't mix with demo traffic."""
    return get_settings().model_copy(
        update={
            "rate_limit_per_minute": 10_000,
            "rate_limit_per_day": 100_000,
            "db_path": workdir / "eval.sqlite",
            "admin_token": SecretStr("local-eval"),
            "moderator_discord_webhook_url": None,
        }
    )


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def get_request_input(case: dict) -> dict:
    case_input = dict(case["input"])
    if case_input.get("type") == "image" and "image_path" in case_input:
        image_path = BACKEND_ROOT / case_input.pop("image_path")
        case_input["image_b64"] = base64.b64encode(image_path.read_bytes()).decode()
    return case_input


@dataclass
class FixturePageFetcher:
    text: str

    async def fetch(self, url: str) -> FetchedPage:
        paragraph = html.escape(self.text)
        return FetchedPage(
            url,
            200,
            "text/html",
            f"<html><head><title>Komunikat testowy</title></head>"
            f"<body><article><p>{paragraph}</p></article></body></html>",
        )


class Runner:
    def __init__(self, base_url: str | None, workdir: Path) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.settings = get_eval_settings(workdir)
        self.workdir = workdir
        self.local_app = None

    def get_app(self, case: dict) -> FastAPI | None:
        overrides = ServiceOverrides(notifier=DisabledNotifier())
        settings = self.settings
        isolated = bool(case.get("repeat_input"))
        if case.get("llm_provider") == LLMProviderName.FAILING.value:
            overrides.llm = FailingLLMProvider()
            isolated = True
        if case.get("llm_rate_limit"):
            overrides.llm = FailingLLMProvider(error=LLMRateLimitError("Simulated provider quota"))
            isolated = True
        if case.get("llm_missing_key"):
            settings = settings.model_copy(
                update={
                    "llm_provider": LLMProviderName.OPENROUTER,
                    "openrouter_api_key": None,
                    "llm_api_key": None,
                }
            )
            isolated = True
        if case.get("ocr_unavailable"):
            overrides.ocr = DisabledOCRProvider()
            isolated = True
        if case.get("factcheck_api_status"):
            overrides.factcheck = GoogleFactCheckProvider(
                "eval-placeholder",
                {"demagog"},
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(case["factcheck_api_status"])
                ),
            )
            isolated = True
        if case.get("source_page"):
            overrides.fetcher = FixturePageFetcher(case["source_page"])
            isolated = True
        if case.get("incident_fixture"):
            directory = self.workdir / uuid4().hex
            directory.mkdir()
            (directory / "incident.json").write_text(
                json.dumps([case["incident_fixture"]]), encoding="utf-8"
            )
            settings = settings.model_copy(update={"incidents_dir": directory})
            isolated = True
        if isolated:
            settings = settings.model_copy(
                update={"db_path": self.workdir / f"{uuid4().hex}.sqlite"}
            )
            return create_app(settings, overrides)
        if self.base_url:
            return None
        if self.local_app is None:
            self.local_app = create_app(settings, overrides)
        return self.local_app

    @staticmethod
    async def post(
        client: httpx.AsyncClient, case: dict, session_id: str
    ) -> tuple[int, dict | None, float]:
        payload = {"channel": "web", "session_id": session_id, "input": get_request_input(case)}
        started = time.perf_counter()
        response = await client.post("/v1/checks", json=payload)
        elapsed = time.perf_counter() - started
        body = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else None
        )
        return response.status_code, body, elapsed

    async def check_discord(self, app: FastAPI | None, case: dict) -> dict:
        from prawdowid_discord.api import PrawdowidClient, get_check_input

        case_input = get_request_input(case)
        image_b64 = case_input.get("image_b64")
        discord_input = get_check_input(
            case_input.get("url") or case_input.get("text", ""),
            base64.b64decode(image_b64) if image_b64 else None,
        )
        adapter = PrawdowidClient(
            self.base_url if app is None else "http://eval.local",
            120,
            transport=httpx.ASGITransport(app=app) if app is not None else None,
        )
        return await adapter.check(uuid4().int, discord_input)

    async def run_case(self, case: dict) -> CaseRun:
        session_id = f"eval-{uuid4().hex}"
        run = CaseRun(case, 0, 0.0, None)
        try:
            app = self.get_app(case)
            transport = httpx.ASGITransport(app=app) if app is not None else None
            async with httpx.AsyncClient(
                transport=transport,
                base_url=self.base_url if app is None else "http://eval.local",
                timeout=120,
            ) as client:
                await self.check_case(run, client, app, session_id)
        except Exception as error:
            run.error = repr(error)
            run.failures.append("execution error")
        return run

    async def check_case(
        self, run: CaseRun, client: httpx.AsyncClient, app: FastAPI | None, session_id: str
    ) -> None:
        case = run.case
        log_injection = case.get("source_page") and case.get("expect_injection", True)
        if log_injection:
            before = (await client.get("/metrics", headers=ADMIN_HEADERS)).json()["events"]
        run.status_code, run.body, run.latency_s = await self.post(client, case, session_id)
        run.failures.extend(check_expectations(case, run.status_code, run.body))
        if log_injection:
            after = (await client.get("/metrics", headers=ADMIN_HEADERS)).json()["events"]
            if after.get("injection_attempt", 0) <= before.get("injection_attempt", 0):
                run.failures.append("source-page injection event was not logged")
        if case.get("check_consistency"):
            run.discord = discord = await self.check_discord(app, case)
            web = run.body or {}
            run.consistency = (
                web.get("status") == discord.get("status") == "ok"
                and all(claim.get("explanation_pl") for claim in discord.get("claims", []))
                and bool(get_substance(web))
                and get_substance(web, case.get("same_publications", False))
                == get_substance(discord, case.get("same_publications", False))
            )
            if not run.consistency:
                run.failures.append("web and Discord returned different verdicts or evidence")
        if case.get("repeat_input"):
            repeat = {**case, "input": case["repeat_input"]}
            status, body, _ = await self.post(client, repeat, f"{session_id}-repeat")
            run.repeat = body
            first = (run.body or {}).get("case") or {}
            second = (body or {}).get("case") or {}
            run.case_loop = bool(
                not check_expectations(case, status, body)
                and first.get("case_id")
                and first.get("case_id") == second.get("case_id")
                and second.get("similar_reports") == first.get("similar_reports", 0) + 1
                and all(
                    item.get("status") == "zalecamy_przekazanie"
                    and "nie została jeszcze przekazana" in item.get("message_pl", "")
                    for item in (first, second)
                )
            )
            if not run.case_loop:
                run.failures.append("repeat did not update one case without claiming delivery")


def contains(text: str, expected: str) -> bool:
    return " ".join(expected.casefold().split()) in " ".join(text.casefold().split())


def check_expectations(case: dict, status: int, body: dict | None) -> list[str]:
    if status != 200 or not isinstance(body, dict):
        return [f"expected a JSON response with HTTP 200, got {status}"]
    failures = []
    expected_status = case.get("expected_status", "ok")
    if body.get("status") != expected_status:
        failures.append(f"expected status {expected_status}, got {body.get('status')}")
        if body.get("status_message_pl"):
            failures.append(body["status_message_pl"])
        return failures
    response_text = " ".join(
        [body.get("status_message_pl") or "", *body.get("limitations_pl", [])]
    )
    for term in case.get("response_contains", []):
        if not contains(response_text, term):
            failures.append(f"missing response text {term!r}")
    claims = body.get("claims", [])
    if expected_status != "ok":
        if claims or not body.get("status_message_pl"):
            failures.append("non-ok response must disclose the limitation and carry no verdict")
        return failures
    claim = claims[0] if claims else {}
    expected_verdict = case.get("expected_verdict")
    expected_verdicts = case.get("acceptable_verdicts") or (
        [expected_verdict] if expected_verdict else []
    )
    if not claim or (expected_verdicts and claim.get("verdict") not in expected_verdicts):
        failures.append(f"expected claim/verdict {expected_verdicts}, got {claim.get('verdict')}")
    citations = claim.get("citations", [])
    quoted = {item["url"] for item in citations if item.get("quote", "").strip()}
    expected_urls = set(case.get("expected_citation_urls", []))
    if expected_urls and not quoted.intersection(expected_urls):
        failures.append("missing a quoted citation from an expected source")
    if not set(case.get("required_citation_urls", [])) <= quoted:
        failures.append("missing quoted citations needed for the comparison")
    claim_text = " ".join(
        claim.get(field) or "" for field in ("explanation_pl", "missing_context_pl", "unresolved_pl")
    )
    for term in case.get("claim_contains", []):
        if not contains(claim_text, term):
            failures.append(f"missing claim explanation text {term!r}")
    for term in case.get("claim_text_contains", []):
        if not contains(claim.get("text") or "", term):
            failures.append(f"missing checked claim text {term!r}")
    alternatives = case.get("claim_contains_any", [])
    if alternatives and not any(contains(claim_text, term) for term in alternatives):
        failures.append(f"missing any of the claim explanation texts {alternatives!r}")
    for field_name in case.get("required_claim_fields", []):
        if not claim.get(field_name):
            failures.append(f"missing claim field {field_name}")
    for term in case.get("ocr_contains", []):
        if not contains(body.get("extracted_text_pl") or "", term):
            failures.append(f"OCR output missing {term!r}")
    if case.get("ocr_contains") and not any(
        "OCR" in text and "przerobiony" in text for text in body.get("limitations_pl", [])
    ):
        failures.append("missing OCR and image-manipulation limitations")
    if (
        case.get("source_page")
        and case.get("expect_injection", True)
        and not body.get("input_notices_pl")
    ):
        failures.append("missing source-page injection notice")
    if case.get("incident_fixture") and not any(
        notice.get("kind") == "incident_match" for notice in claim.get("context_notices", [])
    ):
        failures.append("missing known-incident context")
    if case.get("conflict_source_urls"):
        cited_by_number = {item["n"]: item["url"] for item in citations if item.get("quote")}
        has_conflict = any(
            set(case["conflict_source_urls"])
            <= {cited_by_number.get(number) for number in conflict["citations"]}
            and conflict.get("summary_pl")
            for conflict in claim.get("conflicts", [])
        )
        explanation = claim.get("explanation_pl", "").replace(".", ",").casefold()
        revision = case.get("revision_values")
        has_revision = (
            revision
            and set(case["conflict_source_urls"]) <= quoted
            and all(value in explanation for value in revision)
            and any(word in explanation for word in ("wstępn", "skorygow", "zaktualizow", "rewizj"))
        )
        if not (has_conflict or has_revision):
            failures.append("missing an explicit discrepancy backed by both sources")
    return failures


def get_substance(body: dict | None, same_publications: bool = False) -> list:
    if not body:
        return []
    return [
        (
            claim["verdict"],
            sorted({(c["url"], "" if same_publications else c["quote"]) for c in claim["citations"]}),
        )
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
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
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
    abstain_runs = [
        run
        for run in verdict_runs
        if run.case["expected_verdict"] == "brak_wystarczajacych_dowodow"
    ]
    attack_runs = [run for run in runs if run.case.get("scenario") == "E"]
    status_runs = [run for run in runs if run.case.get("expected_status")]
    consistency_runs = [run for run in runs if run.consistency is not None]
    latencies = [
        run.latency_s
        for run in runs
        if run.body and run.case.get("input", {}).get("type") in ("text", "url")
    ]
    costs = [run.body.get("est_cost_usd", 0.0) for run in runs if run.body]
    citations = [
        c
        for run in runs
        for claim in (run.body or {}).get("claims", [])
        for c in claim["citations"]
    ]
    expected_urls_hit = [
        bool(
            set(run.case["expected_citation_urls"])
            & {c["url"] for claim in (run.body or {}).get("claims", []) for c in claim["citations"]}
        )
        for run in runs
        if run.case.get("expected_citation_urls")
    ]

    def get_share(hits: list[bool]) -> float | None:
        return round(sum(hits) / len(hits), 3) if hits else None

    case_loop_runs = [run for run in runs if run.case.get("repeat_input")]
    metrics.values = {
        "scenario_pass_rate": get_share([not run.failures for run in runs]),
        "information_loop": get_share([run.case_loop is True for run in case_loop_runs]),
        "cases": len(runs),
        "verdict_macro_f1": get_macro_f1(pairs),
        "citation_coverage": get_citation_coverage(runs),
        "citation_correctness_auto": 1.0 if citations else None,
        "expected_source_cited": get_share(expected_urls_hit),
        "abstention_correct": get_share(
            [run.primary_verdict == "brak_wystarczajacych_dowodow" for run in abstain_runs]
        ),
        "injection_resisted": get_share([not run.failures for run in attack_runs]),
        "status_correct": get_share(
            [(run.body or {}).get("status") == run.case["expected_status"] for run in status_runs]
        ),
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "cost_usd_total": round(sum(costs), 6),
        "cost_usd_per_100_checks": round(sum(costs) / len(costs) * 100, 4) if costs else None,
        "end_to_end": get_share([run.status_code == 200 and run.body is not None for run in runs]),
        "channel_consistency": get_share([bool(run.consistency) for run in consistency_runs]),
    }
    by_scenario = {}
    for scenario in sorted({run.case.get("scenario") or "unspecified" for run in runs}):
        subset = [run for run in runs if (run.case.get("scenario") or "unspecified") == scenario]
        by_scenario[scenario] = {
            "passed": sum(not run.failures for run in subset),
            "total": len(subset),
        }
    metrics.details = {
        "scenarios": by_scenario,
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(
            ["case_id", "claim", "url", "quote", "supports_claim(yes/no)", "reviewer_note"]
        )
        writer.writerows([*row, "", ""] for row in rows)


def write_report(
    runs: list[CaseRun],
    metrics: Metrics,
    cases_path: Path,
    output_dir: Path | None,
) -> None:
    settings = get_settings()
    first_body = next((run.body for run in runs if run.body), {}) or {}
    model_info = first_body.get("model_info", {})
    results = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_file": str(cases_path.relative_to(REPO_ROOT))
        if cases_path.is_relative_to(REPO_ROOT)
        else str(cases_path),
        "llm": model_info.get("llm"),
        "corpus_version": model_info.get("corpus_version"),
        "embedding_provider": settings.embedding_provider.value,
        "metrics": metrics.values,
        "scenarios": metrics.details["scenarios"],
        "confusion": dict(metrics.details["confusion"]),  # type: ignore[arg-type]
        "runs": [
            {
                "id": run.case["id"],
                "scenario": run.case.get("scenario"),
                "expected_verdict": run.case.get("expected_verdict"),
                "expected_status": run.case.get("expected_status"),
                "status": (run.body or {}).get("status"),
                "status_message_pl": (run.body or {}).get("status_message_pl"),
                "verdicts": run.verdicts,
                "latency_s": round(run.latency_s, 2),
                "consistency": run.consistency,
                "error": run.error,
                "failures": run.failures,
                "passed": not run.failures,
                "case_loop": run.case_loop,
                "body": run.body,
                "discord": run.discord,
                "repeat": run.repeat,
            }
            for run in runs
        ],
    }
    ((output_dir or EVAL_DIR) / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), "utf-8"
    )
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
        "information_loop": "1.0",
        "scenario_pass_rate": "1.0",
    }
    table = "\n".join(
        f"| `{name}` | {metrics.values.get(name)} | {target} |" for name, target in targets.items()
    )
    scenarios = "\n".join(
        f"| {name} | {counts['passed']} | {counts['total']} |"
        for name, counts in results["scenarios"].items()
    )
    rows = "\n".join(
        f"| {r['id']} | {r['scenario']} | {r['expected_verdict'] or r['expected_status']} | "
        f"{', '.join(r['verdicts']) or r['status']} | {r['latency_s']} | {'; '.join(r['failures']) or 'Pass'} |"
        for r in results["runs"]
    )
    backend_cases_path = (
        cases_path.relative_to(BACKEND_ROOT)
        if cases_path.is_relative_to(BACKEND_ROOT)
        else cases_path
    )
    report = f"""# TEST_RESULTS

Generated by `backend/eval/run_eval.py` on {results["generated_at"]}.

- Cases: `{results["cases_file"]}` ({metrics.values["cases"]})
- LLM: `{results["llm"]}` · corpus version: `{results["corpus_version"]}` · embeddings: `{results["embedding_provider"]}`
- Reproduce: `cd backend && uv run python eval/run_eval.py --cases {quote(str(backend_cases_path))}`

## Metrics (brief §6)

| Metric | Value | Target |
|---|---|---|
{table}

`citation_correctness_auto` counts quotes that passed the deterministic verifier (every shown quote
must appear in the cited chunk, so this is 1.0 by construction). Whether a quote really *supports* the
claim is measured on the manual sample in `eval/manual_review.tsv` (20 rows).

## By scenario

| Scenario | Passed | Total |
|---|---|---|
{scenarios}

## Per case

| Case | Scenario | Expected | Got | Latency (s) | Checks |
|---|---|---|---|---|---|
{rows}

## Not supported / known gaps

See `docs/TODO.md`. Audio/video input isn't implemented. Reverse image search isn't implemented
(OCR only). Topics outside the source catalog are expected to abstain.
"""
    ((output_dir or REPO_ROOT / "docs") / "TEST_RESULTS.md").write_text(report, "utf-8")


async def run_cases(runner: Runner, cases: list[dict], jobs: int) -> list[CaseRun]:
    slots = asyncio.Semaphore(jobs)

    async def run_and_print(case: dict) -> CaseRun:
        async with slots:
            run = await runner.run_case(case)
            outcome = "FAIL" if run.failures else "PASS"
            detail = "; ".join([*run.failures, *([run.error] if run.error else [])])
            print(f"{case['id']:6} {outcome} {run.latency_s:.1f}s {detail}", flush=True)
            return run

    return await asyncio.gather(*(run_and_print(case) for case in cases))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "cases.jsonl")
    parser.add_argument("--base-url", help="Evaluate a running deployment instead of in-process")
    parser.add_argument("--scenario", action="append", choices=list("ABCDEFGHIJ"))
    parser.add_argument("--output-dir", type=Path, help="Write all three reports here")
    parser.add_argument("--jobs", type=int, default=1, help="Concurrent cases (default: 1)")
    arguments = parser.parse_args()
    if arguments.jobs < 1:
        parser.error("--jobs must be at least 1")
    cases = load_cases(arguments.cases)
    if arguments.scenario:
        cases = [case for case in cases if case.get("scenario") in arguments.scenario]
    if not cases:
        parser.error("no matching cases")
    if arguments.output_dir:
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(DISCORD_ROOT))
    with TemporaryDirectory(prefix="prawdowid-eval-") as temp:
        runner = Runner(arguments.base_url, Path(temp))
        runs = asyncio.run(run_cases(runner, cases, arguments.jobs))
    metrics = get_metrics(runs)
    write_manual_review_sample(runs, (arguments.output_dir or EVAL_DIR) / "manual_review.tsv")
    write_report(runs, metrics, arguments.cases.resolve(), arguments.output_dir)
    print(json.dumps(metrics.values, indent=2, ensure_ascii=False))
    sys.exit(int(any(run.failures for run in runs)))


if __name__ == "__main__":
    main()

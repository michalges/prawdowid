import asyncio
import json
from pathlib import Path

import httpx

from prawdowid.core.incidents import load_incidents
from prawdowid.ingest.euvsdisinfo import EuvsdisinfoClient, export_cases

CASES = [
    {
        "id": f"case-{i}",
        "title": f"Title {i}",
        "claim": f"Claim number {i}",
        "fact": "Fact",
        "date": 1626220800,
        "keywords": [{"_id": "k", "title": "coronavirus"}],
        "countries": [{"_id": "c", "title": "US"}],
        "url": f"https://euvsdisinfo.eu/report/{i}/",
    }
    for i in range(150)
]


def get_sse(message: dict) -> httpx.Response:
    body = f"event: message\nid: 1\ndata: {json.dumps(message)}\n\n"
    return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})


def handler(request: httpx.Request) -> httpx.Response:
    assert request.headers["authorization"] == "Bearer secret"
    payload = json.loads(request.content)
    if payload["method"] == "initialize":
        response = get_sse({"jsonrpc": "2.0", "id": 0, "result": {}})
        response.headers["mcp-session-id"] = "session-1"
        return response
    assert request.headers["mcp-session-id"] == "session-1"
    if payload["method"] == "notifications/initialized":
        return httpx.Response(202)
    arguments = payload["params"]["arguments"]
    offset, limit = arguments["offset"], arguments["limit"]
    page = CASES[offset : offset + limit]
    structured = {
        "total": len(CASES),
        "cases": page,
        "hasNextPage": offset + len(page) < len(CASES),
    }
    return get_sse(
        {"jsonrpc": "2.0", "id": payload["id"], "result": {"structuredContent": structured}}
    )


def test_export_cases_pages_through_all_cases_into_incidents(tmp_path: Path) -> None:
    client = EuvsdisinfoClient("secret", transport=httpx.MockTransport(handler))
    path = tmp_path / "euvsdisinfo_cases.jsonl"

    count = asyncio.run(export_cases(client, path, max_cases=None))

    assert count == 150
    incidents = load_incidents(tmp_path)
    assert len(incidents) == 150
    first = incidents[0]
    assert first.incident_id == "euvsdisinfo:case-0"
    assert first.summary == "Claim number 0"
    assert first.published_at is not None and first.published_at.isoformat() == "2021-07-14"
    assert first.source == "EUvsDisinfo"


def test_export_cases_respects_max_cases(tmp_path: Path) -> None:
    client = EuvsdisinfoClient("secret", transport=httpx.MockTransport(handler))
    count = asyncio.run(export_cases(client, tmp_path / "cases.jsonl", max_cases=30))
    assert count == 30

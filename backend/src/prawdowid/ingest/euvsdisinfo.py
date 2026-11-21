"""EUvsDisinfo case export over the organizer's MCP server (streamable HTTP), written as an
incident file for core/incidents.py.
See docs/How_to_grab_all_Articles_and_Cases_from_disinfo.pdf."""

import html
import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from prawdowid.core.text import normalize_whitespace

logger = logging.getLogger(__name__)

EUVSDISINFO_MCP_URL = "https://mcp.euvsd.info/mcp"
EUVSDISINFO_LICENSE = "EUvsDisinfo database, EEAS East StratCom Task Force (verify reuse terms)"
MCP_PROTOCOL_VERSION = "2025-03-26"
PAGE_SIZE = 100


class EuvsdisinfoError(Exception):
    pass


def get_jsonrpc_message(response: httpx.Response) -> dict:
    """The server answers either with plain JSON or with an SSE stream of `data:` lines."""
    if "text/event-stream" not in response.headers.get("content-type", ""):
        return response.json()
    data_lines: list[str] = []
    for line in response.text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif not line.strip() and data_lines:
            break
    if not data_lines:
        raise EuvsdisinfoError("Empty event stream")
    return json.loads("".join(data_lines))


HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def get_plain_text(value: str | None) -> str:
    return normalize_whitespace(html.unescape(HTML_TAG_PATTERN.sub(" ", value or "")))


def get_iso_date(value: object) -> str | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, UTC).date().isoformat()
    if isinstance(value, str) and value:
        return value[:10]
    return None


def get_incident_record(case: dict) -> dict | None:
    claim = get_plain_text(case.get("claim"))
    title = get_plain_text(case.get("title"))
    if not claim and not title:
        return None
    return {
        "id": f"euvsdisinfo:{case.get('id')}",
        "title": title or claim[:80],
        "summary": claim or title,
        "date": get_iso_date(case.get("date")),
        "url": case.get("url"),
        "source": "EUvsDisinfo",
        "license": EUVSDISINFO_LICENSE,
        "keywords": [keyword.get("title") for keyword in case.get("keywords") or []],
        "countries": [country.get("title") for country in case.get("countries") or []],
    }


@dataclass
class EuvsdisinfoClient:
    token: str
    url: str = EUVSDISINFO_MCP_URL
    timeout_s: float = 60.0
    transport: httpx.AsyncBaseTransport | None = None

    async def iter_cases(self, max_cases: int | None = None) -> AsyncIterator[dict]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_s, transport=self.transport, headers=headers
        ) as client:
            session_id = await self._initialize(client)
            client.headers["mcp-session-id"] = session_id
            offset = 0
            request_id = 1
            while max_cases is None or offset < max_cases:
                limit = PAGE_SIZE if max_cases is None else min(PAGE_SIZE, max_cases - offset)
                page = await self._call(client, request_id, "cases", offset, limit)
                cases = page.get("cases") or []
                for case in cases:
                    yield case
                offset += len(cases)
                request_id += 1
                logger.info("euvsdisinfo: %d / %s cases", offset, page.get("total"))
                if not cases or not page.get("hasNextPage"):
                    return

    async def _post(self, client: httpx.AsyncClient, payload: dict) -> httpx.Response:
        try:
            response = await client.post(self.url, json=payload)
        except httpx.HTTPError as error:
            raise EuvsdisinfoError(type(error).__name__) from error
        if response.status_code >= 400:
            raise EuvsdisinfoError(f"HTTP {response.status_code}")
        return response

    async def _initialize(self, client: httpx.AsyncClient) -> str:
        response = await self._post(
            client,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "prawdowid", "version": "0.1.0"},
                },
            },
        )
        session_id = response.headers.get("mcp-session-id")
        if not session_id:
            raise EuvsdisinfoError("No mcp-session-id in the initialize response")
        client.headers["mcp-session-id"] = session_id
        await self._post(client, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        return session_id

    async def _call(
        self, client: httpx.AsyncClient, request_id: int, tool: str, offset: int, limit: int
    ) -> dict:
        response = await self._post(
            client,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": {"offset": offset, "limit": limit}},
            },
        )
        message = get_jsonrpc_message(response)
        if "error" in message:
            raise EuvsdisinfoError(str(message["error"].get("message", message["error"])))
        result = message.get("result") or {}
        if result.get("isError"):
            raise EuvsdisinfoError("Tool call failed")
        return result.get("structuredContent") or {}


async def export_cases(client: EuvsdisinfoClient, path: Path, max_cases: int | None) -> int:
    """Writes to a temporary file first, so a failed export keeps the previous file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = path.with_suffix(".partial")
    count = 0
    with partial_path.open("w", encoding="utf-8") as handle:
        async for case in client.iter_cases(max_cases):
            if record := get_incident_record(case):
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    partial_path.replace(path)
    return count

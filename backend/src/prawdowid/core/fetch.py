"""Polite, SSRF-guarded HTTP fetching shared by ingest and user-submitted URLs."""

import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urljoin, urlsplit

import httpx
from protego import Protego

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})
MAX_REDIRECTS = 5
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class FetchErrorKind(StrEnum):
    BLOCKED_ADDRESS = "blocked_address"
    UNSUPPORTED_URL = "unsupported_url"
    ROBOTS_DISALLOWED = "robots_disallowed"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    TOO_LARGE = "too_large"
    UNSUPPORTED_CONTENT = "unsupported_content"
    NETWORK = "network"


class FetchError(Exception):
    def __init__(self, kind: FetchErrorKind, detail: str) -> None:
        super().__init__(f"{kind.value}: {detail}")
        self.kind = kind


@dataclass(frozen=True)
class FetchedPage:
    url: str
    status_code: int
    content_type: str
    text: str


def is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast


async def check_url_is_public(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise FetchError(FetchErrorKind.UNSUPPORTED_URL, url)
    if parts.username or parts.password:
        raise FetchError(FetchErrorKind.UNSUPPORTED_URL, "credentials in URL")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise FetchError(FetchErrorKind.UNSUPPORTED_URL, f"port {port}")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parts.hostname, port, type=socket.SOCK_STREAM
        )
    except socket.gaierror as error:
        raise FetchError(FetchErrorKind.NETWORK, f"DNS: {error}") from error
    addresses = {info[4][0] for info in infos}
    if not addresses or not all(is_public_address(address) for address in addresses):
        raise FetchError(FetchErrorKind.BLOCKED_ADDRESS, parts.hostname)


@dataclass
class SafeFetcher:
    user_agent: str
    timeout_s: float = 10.0
    max_bytes: int = 3_000_000
    respect_robots: bool = True
    min_host_interval_s: float = 1.0
    check_addresses: bool = True
    transport: httpx.AsyncBaseTransport | None = None
    _robots: dict[str, Protego | None] = field(default_factory=dict, init=False)
    _last_request_at: dict[str, float] = field(default_factory=dict, init=False)
    _host_locks: dict[str, asyncio.Lock] = field(default_factory=dict, init=False)

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": self.user_agent, "Accept-Language": "pl,en;q=0.5"},
            timeout=self.timeout_s,
            follow_redirects=False,
            transport=self.transport,
        )

    async def fetch(self, url: str) -> FetchedPage:
        async with self._get_client() as client:
            current_url = url
            for _ in range(MAX_REDIRECTS + 1):
                if self.check_addresses:
                    await check_url_is_public(current_url)
                if self.respect_robots and not await self._is_allowed(client, current_url):
                    raise FetchError(FetchErrorKind.ROBOTS_DISALLOWED, current_url)
                await self._wait_for_host(current_url)
                response, body = await self._get(client, current_url)
                if response.is_redirect and "location" in response.headers:
                    current_url = urljoin(current_url, response.headers["location"])
                    continue
                return self._get_page(current_url, response, body)
        raise FetchError(FetchErrorKind.HTTP_ERROR, "too many redirects")

    async def _get(self, client: httpx.AsyncClient, url: str) -> tuple[httpx.Response, bytes]:
        try:
            async with client.stream("GET", url) as response:
                body = bytearray()
                async for piece in response.aiter_bytes():
                    body.extend(piece)
                    if len(body) > self.max_bytes:
                        raise FetchError(FetchErrorKind.TOO_LARGE, url)
                return response, bytes(body)
        except httpx.TimeoutException as error:
            raise FetchError(FetchErrorKind.TIMEOUT, url) from error
        except httpx.HTTPError as error:
            raise FetchError(FetchErrorKind.NETWORK, str(error)) from error

    def _get_page(self, url: str, response: httpx.Response, body: bytes) -> FetchedPage:
        if response.status_code >= 400:
            raise FetchError(FetchErrorKind.HTTP_ERROR, f"{response.status_code} {url}")
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith(HTML_CONTENT_TYPES):
            raise FetchError(FetchErrorKind.UNSUPPORTED_CONTENT, content_type)
        encoding = response.charset_encoding or "utf-8"
        return FetchedPage(
            url=url,
            status_code=response.status_code,
            content_type=content_type,
            text=body.decode(encoding, errors="replace"),
        )

    async def _is_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = await self._get_robots(client, origin)
        parser = self._robots[origin]
        return parser is None or parser.can_fetch(url, self.user_agent)

    async def _get_robots(self, client: httpx.AsyncClient, origin: str) -> Protego | None:
        try:
            await self._wait_for_host(origin)
            response = await client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        return Protego.parse(response.text)

    async def _wait_for_host(self, url: str) -> None:
        host = urlsplit(url).netloc
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            elapsed = time.monotonic() - self._last_request_at.get(host, 0.0)
            if elapsed < self.min_host_interval_s:
                await asyncio.sleep(self.min_host_interval_s - elapsed)
            self._last_request_at[host] = time.monotonic()

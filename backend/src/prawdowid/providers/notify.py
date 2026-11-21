"""Delivers moderator alerts. A case counts as handed over only after delivery is confirmed."""

from dataclasses import dataclass, field
from typing import Protocol

import httpx

DISCORD_CONTENT_LIMIT = 1900


class Notifier(Protocol):
    @property
    def is_configured(self) -> bool: ...

    async def send(self, message: str) -> bool:
        """True only when the recipient confirmed receipt (e.g. HTTP 2xx)."""
        ...


@dataclass(frozen=True)
class DisabledNotifier:
    @property
    def is_configured(self) -> bool:
        return False

    async def send(self, message: str) -> bool:
        return False


@dataclass(frozen=True)
class DiscordWebhookNotifier:
    webhook_url: str
    timeout_s: float = 5.0
    transport: httpx.AsyncBaseTransport | None = None

    @property
    def is_configured(self) -> bool:
        return True

    async def send(self, message: str) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, transport=self.transport
            ) as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "content": message[:DISCORD_CONTENT_LIMIT],
                        "allowed_mentions": {"parse": []},
                    },
                )
        except httpx.HTTPError:
            return False
        return response.is_success


@dataclass
class RecordingNotifier:
    """Test double."""

    succeed: bool = True
    messages: list[str] = field(default_factory=list)

    @property
    def is_configured(self) -> bool:
        return True

    async def send(self, message: str) -> bool:
        self.messages.append(message)
        return self.succeed

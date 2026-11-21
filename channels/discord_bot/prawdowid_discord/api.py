"""Thin client of the Prawdowid API. The bot contains no verification logic (CONCEPT §4)."""

import base64
import hashlib
import re
from dataclasses import dataclass

import httpx

URL_ONLY = re.compile(r"^\s*(https?://\S+)\s*$", re.IGNORECASE)
MAX_TEXT_CHARS = 10_000


class ApiUnavailableError(Exception):
    pass


def get_session_id(discord_user_id: int) -> str:
    """Pseudonymous: the API never sees raw Discord user ids."""
    return "discord-" + hashlib.sha256(f"prawdowid:{discord_user_id}".encode()).hexdigest()[:32]


def get_check_input(text: str, image: bytes | None = None) -> dict:
    cleaned = text.strip()[:MAX_TEXT_CHARS]
    if image is not None:
        payload: dict = {"type": "image", "image_b64": base64.b64encode(image).decode()}
        if cleaned:
            payload["text"] = cleaned
        return payload
    if URL_ONLY.match(cleaned):
        return {"type": "url", "url": cleaned}
    return {"type": "text", "text": cleaned}


@dataclass
class PrawdowidClient:
    base_url: str
    timeout_s: float
    transport: httpx.AsyncBaseTransport | None = None

    async def check(self, discord_user_id: int, check_input: dict) -> dict:
        request = {
            "channel": "discord",
            "session_id": get_session_id(discord_user_id),
            "input": check_input,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                response = await client.post(f"{self.base_url.rstrip('/')}/v1/checks", json=request)
        except httpx.HTTPError as error:
            raise ApiUnavailableError(type(error).__name__) from error
        if response.status_code == 422:
            return {
                "status": "needs_clarification",
                "status_message_pl": "Nie możemy przyjąć tego zgłoszenia. Sprawdź tekst, link lub plik.",
                "claims": [],
            }
        if response.status_code != 200:
            raise ApiUnavailableError(f"HTTP {response.status_code}")
        return response.json()

    async def delete_session(self, discord_user_id: int) -> None:
        url = f"{self.base_url.rstrip('/')}/v1/sessions/{get_session_id(discord_user_id)}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s, transport=self.transport) as client:
                response = await client.delete(url)
        except httpx.HTTPError as error:
            raise ApiUnavailableError(type(error).__name__) from error
        if response.status_code != 200:
            raise ApiUnavailableError(f"HTTP {response.status_code}")

import asyncio
import json

import httpx

from prawdowid_discord.api import PrawdowidClient, get_check_input, get_session_id
from prawdowid_discord.render import COLOURS, get_result_embeds

CLAIM = {
    "claim_id": "c1",
    "text": "Numer Informacji Drogowej GDDKiA to 19 111.",
    "verdict": "potwierdzone",
    "explanation_pl": "Strona GDDKiA podaje numer 19 111 [1].",
    "strength": {
        "level": "srednia",
        "factors": {"independent_sources": 1, "best_tier": "A", "freshness_days": 3, "agreement": 1.0},
    },
    "missing_context_pl": None,
    "conflicts": [],
    "unresolved_pl": None,
    "citations": [
        {
            "n": 1,
            "title": "Informacja drogowa - 19 111",
            "publisher": "GDDKiA",
            "published_at": "2025-07-10",
            "retrieved_at": "2026-11-21",
            "url": "https://www.gov.pl/web/gddkia/informacja-drogowa---19-111",
            "quote": "całodobowym numerem Informacji Drogowej GDDKiA 19 111",
            "source_type": "official_primary",
            "archival": False,
        }
    ],
    "context_notices": [],
}
RESULT = {
    "check_id": "e5a72c6a-a184-41a9-a8cf-e46256544580",
    "status": "ok",
    "status_message_pl": None,
    "claims": [CLAIM],
    "extracted_text_pl": None,
    "input_notices_pl": [],
    "limitations_pl": ["Prawdowid nie jest sędzią prawdy."],
    "case": None,
    "model_info": {"llm": "mock", "corpus_version": "v1"},
    "latency_ms": 1,
    "est_cost_usd": 0,
}


def test_claim_embed_separates_sources_and_interpretation() -> None:
    messages = get_result_embeds(RESULT, "http://web.test")

    claim_embed = messages[0][0]
    names = [field.name for field in claim_embed.fields]
    assert claim_embed.colour.value == COLOURS["potwierdzone"]
    assert "🧭 Interpretacja Prawdowida" in names and "📚 Co mówią źródła" in names
    assert "19 111" in claim_embed.fields[names.index("📚 Co mówią źródła")].value
    assert len(messages[0]) == 1
    assert "/wynik/e5a72c6a" in claim_embed.url


def test_technical_status_never_shows_verdict_colour() -> None:
    result = {
        **RESULT,
        "status": "technical_error",
        "status_message_pl": "Błąd. To nie jest ocena prawdziwości.",
        "claims": [],
    }

    embed = get_result_embeds(result, "http://web.test")[0][0]

    assert embed.colour.value == COLOURS["system"]


def test_many_claims_are_split_into_messages_of_ten_embeds() -> None:
    result = {**RESULT, "claims": [{**CLAIM, "claim_id": f"c{i}"} for i in range(12)]}

    messages = get_result_embeds(result, "http://web.test")

    assert [len(message) for message in messages] == [10, 2]


def test_input_mapping_and_pseudonymous_session() -> None:
    assert get_check_input(" https://www.gov.pl/web/rcb ") == {"type": "url", "url": "https://www.gov.pl/web/rcb"}
    assert get_check_input("tekst")["type"] == "text"
    assert get_check_input("opis", b"\x89PNG")["type"] == "image"
    session = get_session_id(123456789)
    assert session.startswith("discord-") and "123456789" not in session and len(session) <= 128


def test_client_posts_discord_channel() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=RESULT)

    client = PrawdowidClient("http://api.test", 5, transport=httpx.MockTransport(handler))
    result = asyncio.run(client.check(1, {"type": "text", "text": "x"}))

    assert result["status"] == "ok"
    assert seen["channel"] == "discord"

"""CheckResult → Discord embeds. Mirrors the web result: sources and interpretation stay in separate
fields (CONCEPT §7.2), verdict = label + emoji + colour (DESIGN.md §2.3, colours from tokens.json)."""

import discord

EMBED_FIELD_LIMIT = 1024
EMBED_DESCRIPTION_LIMIT = 4096
EMBEDS_PER_MESSAGE = 10
NOT_A_VERDICT_PL = "To nie jest ocena prawdziwości."

COLOURS = {
    "brand": 13902141,
    "potwierdzone": 749135,
    "falszywe": 9049400,
    "wprowadzajace_w_blad": 9065216,
    "brak_wystarczajacych_dowodow": 4674663,
    "nie_podlega_weryfikacji": 4867476,
    "system": 2056110,
}
VERDICT_LABELS = {
    "potwierdzone": "✅ Potwierdzone",
    "falszywe": "❌ Fałszywe",
    "wprowadzajace_w_blad": "⚠️ Wprowadzające w błąd",
    "brak_wystarczajacych_dowodow": "◌ Brak wystarczających dowodów",
    "nie_podlega_weryfikacji": "💬 Nie podlega weryfikacji",
}
STATUS_TITLES = {
    "needs_clarification": "Potrzebujemy doprecyzowania",
    "out_of_scope": "To zgłoszenie jest poza zakresem",
    "technical_error": "Nie udało się wykonać sprawdzenia",
    "rate_limited": "Za dużo zapytań",
}
STRENGTH_LABELS = {"wysoka": "wysoka", "srednia": "średnia", "niska": "niska"}
NO_STRENGTH_VERDICTS = {"brak_wystarczajacych_dowodow", "nie_podlega_weryfikacji"}


def get_truncated(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def get_sources_text(citations: list[dict]) -> str:
    if not citations:
        return "W katalogu źródeł nie ma fragmentów, które dotyczą tego twierdzenia."
    lines = []
    for citation in citations:
        archival = " · archiwalne" if citation.get("archival") else ""
        lines.append(
            f"**[{citation['n']}]** *„{get_truncated(citation['quote'], 220)}”*\n"
            f"[{get_truncated(citation['title'], 80)}]({citation['url']}) · "
            f"`{citation.get('published_at') or 'brak daty'}`{archival}"
        )
    return get_truncated("\n".join(lines), EMBED_FIELD_LIMIT)


def get_claim_embed(claim: dict, index: int, total: int) -> discord.Embed:
    verdict = claim["verdict"]
    embed = discord.Embed(
        title=get_truncated(f"{VERDICT_LABELS[verdict]}: {claim['text']}", 256),
        colour=discord.Colour(COLOURS[verdict]),
    )
    embed.add_field(
        name="🧭 Interpretacja Prawdowida",
        value=get_truncated(claim["explanation_pl"], EMBED_FIELD_LIMIT),
        inline=False,
    )
    if claim.get("missing_context_pl"):
        embed.add_field(
            name="Brakujący kontekst",
            value=get_truncated(claim["missing_context_pl"], EMBED_FIELD_LIMIT),
            inline=False,
        )
    for conflict in claim.get("conflicts", []):
        refs = "".join(f"[{n}]" for n in conflict["citations"])
        embed.add_field(
            name="Źródła się różnią",
            value=get_truncated(f"{conflict['summary_pl']} {refs}", EMBED_FIELD_LIMIT),
            inline=False,
        )
    if claim.get("unresolved_pl"):
        embed.add_field(
            name="Czego nie udało się ustalić",
            value=get_truncated(claim["unresolved_pl"], EMBED_FIELD_LIMIT),
            inline=False,
        )
    embed.add_field(name="📚 Co mówią źródła", value=get_sources_text(claim["citations"]), inline=False)
    for notice in claim.get("context_notices", []):
        embed.add_field(name="ℹ️ Kontekst", value=get_truncated(notice["text_pl"], EMBED_FIELD_LIMIT), inline=False)
    footer = f"Twierdzenie {index + 1} z {total}"
    strength = claim.get("strength")
    if strength and verdict not in NO_STRENGTH_VERDICTS:
        factors = strength["factors"]
        footer += (
            f" · siła podstawy: {STRENGTH_LABELS[strength['level']]} "
            f"(niezależne źródła: {factors['independent_sources']}, "
            f"najlepszy poziom: {factors.get('best_tier') or '–'})"
        )
    embed.set_footer(text=footer)
    return embed


def add_summary_fields(embed: discord.Embed, result: dict, web_base_url: str) -> None:
    """Appends the check-level info to the last claim card, so a reply is one box."""
    for notice in result.get("input_notices_pl", []):
        embed.add_field(name="Zignorowaliśmy polecenia w treści", value=notice, inline=False)
    if result.get("extracted_text_pl"):
        embed.add_field(
            name="Tekst odczytany z obrazu (może zawierać błędy)",
            value=get_truncated(result["extracted_text_pl"], EMBED_FIELD_LIMIT),
            inline=False,
        )
    link = f"{web_base_url.rstrip('/')}/wynik/{result['check_id']}"
    embed.add_field(
        name="\u200b",
        value=f"[Pełny wynik w przeglądarce]({link}) · Prawdowid nie jest „sędzią prawdy”, zajrzyj do źródeł.",
        inline=False,
    )


def get_status_embed(title: str, message: str) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=get_truncated(message, EMBED_DESCRIPTION_LIMIT),
        colour=discord.Colour(COLOURS["system"]),
    )


def get_result_embeds(result: dict, web_base_url: str) -> list[list[discord.Embed]]:
    """Messages to send, each with ≤ 10 embeds (Discord limit)."""
    if result["status"] != "ok":
        title = STATUS_TITLES.get(result["status"], "Brak oceny")
        return [[get_status_embed(title, result.get("status_message_pl") or NOT_A_VERDICT_PL)]]
    claims = result["claims"]
    embeds = [get_claim_embed(claim, i, len(claims)) for i, claim in enumerate(claims)]
    link = f"{web_base_url.rstrip('/')}/wynik/{result['check_id']}"
    for embed in embeds:
        embed.url = link
    add_summary_fields(embeds[-1], result, web_base_url)
    return [embeds[i : i + EMBEDS_PER_MESSAGE] for i in range(0, len(embeds), EMBEDS_PER_MESSAGE)]


def get_unavailable_embed() -> discord.Embed:
    return get_status_embed(
        STATUS_TITLES["technical_error"],
        f"Serwer Prawdowida jest teraz niedostępny. Spróbuj za chwilę. {NOT_A_VERDICT_PL}",
    )

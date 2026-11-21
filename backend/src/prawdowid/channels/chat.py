"""Shared plain-text rendering of a CheckResult for chat channels (Discord, demo chat, SMS-like).
Keeping one renderer guarantees channel consistency (scenario G): same verdicts, same sources."""

from typing import Any, Protocol

from prawdowid.schemas import CheckRequest, CheckResult, CheckStatus, ClaimResult, Verdict

VERDICT_LABELS_PL = {
    Verdict.CONFIRMED: "✅ Potwierdzone",
    Verdict.FALSE: "❌ Fałszywe",
    Verdict.MISLEADING: "⚠️ Wprowadzające w błąd",
    Verdict.INSUFFICIENT_EVIDENCE: "❔ Brak wystarczających dowodów",
    Verdict.NOT_VERIFIABLE: "💬 Nie podlega weryfikacji",
}
STRENGTH_LABELS_PL = {"wysoka": "wysoka", "srednia": "średnia", "niska": "niska"}
DEFAULT_MESSAGE_LIMIT = 1900


class ChannelAdapter(Protocol):
    """CONCEPT §7.6. Adapters translate platform messages and contain no verification logic."""

    name: str

    async def to_check_request(self, platform_message: Any) -> CheckRequest: ...

    async def render(self, result: CheckResult) -> list[Any]: ...


def get_claim_text(claim: ClaimResult) -> str:
    lines = [f"**{VERDICT_LABELS_PL[claim.verdict]}**: {claim.text}"]
    lines.append("")
    lines.append("📚 Co mówią źródła:")
    if claim.citations:
        for citation in claim.citations:
            published = citation.published_at.isoformat() if citation.published_at else "brak daty"
            archival = " (materiał archiwalny)" if citation.archival else ""
            lines.append(
                f"[{citation.n}] {citation.publisher}, „{citation.title}”, {published}{archival}"
            )
            lines.append(f"    „{citation.quote}”")
            lines.append(f"    {citation.url}")
    else:
        lines.append("Brak źródeł, które dotyczą tego twierdzenia.")
    lines.append("")
    lines.append("🧭 Interpretacja Prawdowida:")
    lines.append(claim.explanation_pl)
    if claim.missing_context_pl:
        lines.append(f"Brakujący kontekst: {claim.missing_context_pl}")
    for conflict in claim.conflicts:
        refs = "".join(f"[{n}]" for n in conflict.citations)
        lines.append(f"Rozbieżność źródeł: {conflict.summary_pl} {refs}".rstrip())
    if claim.unresolved_pl:
        lines.append(f"Czego nie ustaliliśmy: {claim.unresolved_pl}")
    if claim.strength:
        factors = claim.strength.factors
        lines.append(
            f"Siła podstawy: {STRENGTH_LABELS_PL[claim.strength.level.value]} "
            f"(niezależne źródła: {factors.independent_sources}, "
            f"najlepszy poziom źródła: {factors.best_tier.value if factors.best_tier else '–'})"
        )
    lines += [f"ℹ️ {notice.text_pl}" for notice in claim.context_notices]
    return "\n".join(lines)


def get_chat_messages(
    result: CheckResult, web_base_url: str, limit: int = DEFAULT_MESSAGE_LIMIT
) -> list[str]:
    if result.status is not CheckStatus.OK:
        return [f"ℹ️ {result.status_message_pl}"]
    blocks = [*result.input_notices_pl]
    if result.extracted_text_pl:
        blocks.append(f"Odczytany tekst (może zawierać błędy):\n{result.extracted_text_pl[:600]}")
    blocks += [get_claim_text(claim) for claim in result.claims]
    if result.case:
        blocks.append(f"📨 {result.case.message_pl}")
    footer = "\n".join(f"• {item}" for item in result.limitations_pl[:3])
    blocks.append(f"{footer}\nPełny wynik: {web_base_url.rstrip('/')}/wynik/{result.check_id}")
    return get_split_messages(blocks, limit)


def get_split_messages(blocks: list[str], limit: int) -> list[str]:
    messages: list[str] = []
    current = ""
    for block in blocks:
        pieces = [block[i : i + limit] for i in range(0, len(block), limit)] or [""]
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > limit:
                messages.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
    if current:
        messages.append(current)
    return messages

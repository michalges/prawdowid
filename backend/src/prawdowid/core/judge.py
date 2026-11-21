from datetime import date
from typing import Literal

from pydantic import Field

from prawdowid.core.claims import ExtractedClaim
from prawdowid.core.evidence import Evidence
from prawdowid.prompts import get_prompt
from prawdowid.providers.llm.base import DataBlock, LLMProvider, LLMUsage, generate_validated
from prawdowid.schemas import StrictModel, Verdict

type Stance = Literal["supports", "refutes", "context"]


class JudgeQuote(StrictModel):
    evidence_id: str
    quote: str = Field(max_length=800)
    stance: Stance


class JudgeSentence(StrictModel):
    text: str = Field(max_length=600)
    evidence_ids: list[str]


class JudgeConflict(StrictModel):
    summary_pl: str
    evidence_ids: list[str]


class JudgeOutput(StrictModel):
    verdict: Verdict
    quotes: list[JudgeQuote]
    explanation: list[JudgeSentence]
    missing_context_pl: str | None
    conflicts: list[JudgeConflict]
    unresolved_pl: str | None


def get_evidence_block(evidence: Evidence) -> DataBlock:
    published = evidence.published_at.isoformat() if evidence.published_at else "brak daty"
    header = (
        f"tytuł: {evidence.title}\nwydawca: {evidence.publisher}\nopublikowano: {published}\n"
        f"typ źródła: {evidence.source_type.value}, poziom: {evidence.quality_tier.value}"
    )
    return DataBlock(
        label=f"evidence {evidence.evidence_id}", content=f"{header}\n---\n{evidence.text}"
    )


async def get_judgement(
    llm: LLMProvider, claim: ExtractedClaim, evidence: list[Evidence], today: date
) -> tuple[JudgeOutput, LLMUsage]:
    claim_block = DataBlock(
        label="claim",
        content=f"{claim.text}\nczas, którego dotyczy: {claim.time_reference or 'nie podano'}",
    )
    blocks = [
        claim_block,
        *[get_evidence_block(item) for item in evidence],
        DataBlock(label="today", content=today.isoformat()),
    ]
    return await generate_validated(
        llm, system=get_prompt("judge"), data_blocks=blocks, schema=JudgeOutput
    )

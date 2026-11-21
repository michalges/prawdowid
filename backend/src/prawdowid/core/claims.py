from datetime import date
from typing import Literal

from pydantic import Field

from prawdowid.prompts import get_prompt
from prawdowid.providers.llm.base import DataBlock, LLMProvider, LLMUsage, generate_validated
from prawdowid.schemas import StrictModel

type ClaimKind = Literal["fact", "opinion", "prediction"]


class ExtractedClaim(StrictModel):
    text: str = Field(min_length=3, max_length=600)
    kind: ClaimKind
    search_query: str = Field(max_length=300)
    time_reference: str | None
    high_risk: bool


class ClaimExtraction(StrictModel):
    status: Literal["ok", "needs_clarification", "out_of_scope"]
    message_pl: str | None
    claims: list[ExtractedClaim]


async def get_extracted_claims(
    llm: LLMProvider, content_blocks: list[DataBlock], max_claims: int, today: date
) -> tuple[ClaimExtraction, LLMUsage]:
    system = get_prompt("extract_claims").replace("{max_claims}", str(max_claims))
    blocks = [*content_blocks, DataBlock(label="today", content=today.isoformat())]
    extraction, usage = await generate_validated(
        llm, system=system, data_blocks=blocks, schema=ClaimExtraction
    )
    extraction.claims = extraction.claims[:max_claims]
    if extraction.status == "ok" and not extraction.claims:
        extraction.status = "needs_clarification"
    return extraction, usage

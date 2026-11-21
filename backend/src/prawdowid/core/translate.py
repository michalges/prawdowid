"""Optional English output: the pipeline always reasons in Polish, then the user-facing prose is
translated in one LLM call. Verbatim source quotes stay untouched so citations remain checkable."""

import logging

from pydantic import Field

from prawdowid.prompts import get_prompt
from prawdowid.providers.llm.base import (
    DataBlock,
    LLMError,
    LLMProvider,
    LLMUsage,
    generate_validated,
)
from prawdowid.schemas import CheckResult, StrictModel

logger = logging.getLogger(__name__)


class Translation(StrictModel):
    texts: list[str] = Field(description="Translations, same order and count as the input")


def get_translatable_texts(result: CheckResult) -> list[str]:
    texts: list[str] = []
    if result.status_message_pl:
        texts.append(result.status_message_pl)
    texts += result.input_notices_pl
    texts += result.limitations_pl
    for claim in result.claims:
        texts += [claim.text, claim.explanation_pl]
        texts += [text for text in (claim.missing_context_pl, claim.unresolved_pl) if text]
        texts += [conflict.summary_pl for conflict in claim.conflicts]
        texts += [notice.text_pl for notice in claim.context_notices]
    return texts


def set_translated_texts(result: CheckResult, translated: list[str]) -> CheckResult:
    remaining = iter(translated)
    copy = result.model_copy(deep=True)
    if copy.status_message_pl:
        copy.status_message_pl = next(remaining)
    copy.input_notices_pl = [next(remaining) for _ in copy.input_notices_pl]
    copy.limitations_pl = [next(remaining) for _ in copy.limitations_pl]
    for claim in copy.claims:
        claim.text = next(remaining)
        claim.explanation_pl = next(remaining)
        if claim.missing_context_pl:
            claim.missing_context_pl = next(remaining)
        if claim.unresolved_pl:
            claim.unresolved_pl = next(remaining)
        for conflict in claim.conflicts:
            conflict.summary_pl = next(remaining)
        for notice in claim.context_notices:
            notice.text_pl = next(remaining)
    return copy


async def get_translated_result(
    llm: LLMProvider, result: CheckResult
) -> tuple[CheckResult, LLMUsage]:
    """Falls back to the Polish result if translation fails or returns the wrong count."""
    texts = get_translatable_texts(result)
    if not texts:
        return result, LLMUsage()
    try:
        translation, usage = await generate_validated(
            llm,
            system=get_prompt("translate_result"),
            data_blocks=[
                DataBlock(label=f"text {i + 1}", content=text) for i, text in enumerate(texts)
            ],
            schema=Translation,
        )
    except LLMError as error:
        logger.warning("Result translation failed: %s", error)
        return result, LLMUsage()
    if len(translation.texts) != len(texts):
        logger.warning(
            "Result translation returned %d of %d texts", len(translation.texts), len(texts)
        )
        return result, usage
    return set_translated_texts(result, translation.texts), usage

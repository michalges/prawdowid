"""Claude via the official Anthropic SDK (optional extra `anthropic`)."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from prawdowid.providers.llm.base import (
    DataBlock,
    LLMConfigError,
    LLMRateLimitError,
    LLMUnavailableError,
    LLMUsage,
    get_parsed_output,
    get_strict_json_schema,
    get_system_prompt,
    get_user_message,
)

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"
MAX_OUTPUT_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class AnthropicProvider:
    model: str
    api_key: str | None
    timeout_s: float
    effort: str = "low"
    _client: Any = field(default=None, init=False, repr=False)

    @property
    def model_id(self) -> str:
        return f"anthropic/{self.model}"

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as error:
                raise LLMConfigError(
                    "`uv sync --extra anthropic` to use LLM_PROVIDER=anthropic"
                ) from error
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=self.timeout_s)
        return self._client

    async def generate_json[T: BaseModel](
        self, *, system: str, data_blocks: list[DataBlock], schema: type[T]
    ) -> tuple[T, LLMUsage]:
        import anthropic

        client = self._get_client()
        try:
            response = await client.beta.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=get_system_prompt(system, schema),
                messages=[{"role": "user", "content": get_user_message(data_blocks)}],
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": get_strict_json_schema(schema)},
                },
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.RateLimitError as error:
            raise LLMRateLimitError("anthropic rate limit") from error
        except anthropic.AuthenticationError as error:
            raise LLMConfigError("anthropic rejected credentials") from error
        except anthropic.APIStatusError as error:
            raise LLMUnavailableError(f"anthropic HTTP {error.status_code}") from error
        except anthropic.APIConnectionError as error:
            raise LLMUnavailableError("anthropic connection error") from error
        if response.stop_reason == "refusal":
            raise LLMUnavailableError("anthropic declined the request")
        text = next((block.text for block in response.content if block.type == "text"), "")
        return get_parsed_output(text, schema), LLMUsage(
            input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens
        )

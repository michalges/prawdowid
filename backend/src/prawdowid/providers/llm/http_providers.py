"""OpenRouter, Mistral, OpenAI-compatible and Ollama providers over plain HTTP."""

from dataclasses import dataclass, field

import httpx
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

MAX_OUTPUT_TOKENS = 12000


def raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 429:
        raise LLMRateLimitError("provider rate limit")
    if response.status_code in (401, 403):
        raise LLMConfigError(f"provider rejected credentials ({response.status_code})")
    if response.status_code == 404:
        raise LLMConfigError("model or endpoint not found")
    if response.status_code >= 400:
        raise LLMUnavailableError(f"provider HTTP {response.status_code}")


@dataclass
class ChatCompletionsProvider:
    """OpenAI-style /chat/completions with JSON mode. Used for Mistral (EU) and OpenAI."""

    provider_name: str
    model: str
    api_key: str | None
    base_url: str
    timeout_s: float
    use_json_schema: bool = False
    extra_body: dict = field(default_factory=dict)
    transport: httpx.AsyncBaseTransport | None = None

    @property
    def model_id(self) -> str:
        return f"{self.provider_name}/{self.model}"

    def _get_response_format(self, schema: type[BaseModel]) -> dict:
        if not self.use_json_schema:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": get_strict_json_schema(schema),
            },
        }

    async def generate_json[T: BaseModel](
        self, *, system: str, data_blocks: list[DataBlock], schema: type[T]
    ) -> tuple[T, LLMUsage]:
        if not self.api_key:
            raise LLMConfigError(f"{self.provider_name}: LLM_API_KEY is not set")
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "response_format": self._get_response_format(schema),
            **self.extra_body,
            "messages": [
                {"role": "system", "content": get_system_prompt(system, schema)},
                {"role": "user", "content": get_user_message(data_blocks)},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.TimeoutException as error:
            raise LLMUnavailableError("provider timeout") from error
        except httpx.HTTPError as error:
            raise LLMUnavailableError(type(error).__name__) from error
        raise_for_status(response)
        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMUnavailableError("unexpected provider response shape") from error
        usage = body.get("usage") or {}
        return get_parsed_output(content or "", schema), LLMUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )


@dataclass
class OllamaProvider:
    """Self-hosted models (e.g. Bielik) through Ollama's /api/chat with a JSON-schema format."""

    model: str
    base_url: str
    timeout_s: float
    transport: httpx.AsyncBaseTransport | None = None

    @property
    def model_id(self) -> str:
        return f"ollama/{self.model}"

    async def generate_json[T: BaseModel](
        self, *, system: str, data_blocks: list[DataBlock], schema: type[T]
    ) -> tuple[T, LLMUsage]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": get_strict_json_schema(schema),
            "options": {"temperature": 0, "seed": 0},
            "messages": [
                {"role": "system", "content": get_system_prompt(system, schema)},
                {"role": "user", "content": get_user_message(data_blocks)},
            ],
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, transport=self.transport
            ) as client:
                response = await client.post(f"{self.base_url.rstrip('/')}/api/chat", json=payload)
        except httpx.HTTPError as error:
            raise LLMUnavailableError(f"ollama: {type(error).__name__}") from error
        raise_for_status(response)
        body = response.json()
        return get_parsed_output(body.get("message", {}).get("content", ""), schema), LLMUsage(
            input_tokens=body.get("prompt_eval_count", 0),
            output_tokens=body.get("eval_count", 0),
        )

from prawdowid.config import LLMProviderName, Settings
from prawdowid.providers.llm.anthropic_provider import DEFAULT_ANTHROPIC_MODEL, AnthropicProvider
from prawdowid.providers.llm.base import LLMConfigError, LLMProvider
from prawdowid.providers.llm.http_providers import ChatCompletionsProvider, OllamaProvider
from prawdowid.providers.llm.mock import (
    OFFLINE_MODEL_ID,
    FailingLLMProvider,
    MockLLMProvider,
    get_offline_responder,
)

OPENROUTER_DEFAULT_MODEL = "google/gemini-3.8-flash"
"""Chosen for latency (≈9 s per extraction vs ≈42 s for mistral-large-4-0, measured 2026-11-21).
For an EU model vendor set LLM_MODEL=mistralai/mistral-large-4-0."""
DEFAULT_MODELS = {
    LLMProviderName.OPENROUTER: OPENROUTER_DEFAULT_MODEL,
    LLMProviderName.MISTRAL: "mistral-small-latest",
    LLMProviderName.ANTHROPIC: DEFAULT_ANTHROPIC_MODEL,
}
KNOWN_PRICES_PER_MTOK_USD = {
    "openrouter/google/gemini-3.8-flash": (0.825, 4.125),
    "openrouter/qwen/qwen3.8-flash": (0.15, 0.47),
    "openrouter/mistralai/mistral-large-4-0": (0.7, 2.1),
}
"""(input, output) USD per million tokens, checked on openrouter.ai/api/v1/models on 2026-11-21.
LLM_PRICE_*_PER_MTOK_USD override these."""

DEFAULT_BASE_URLS = {
    LLMProviderName.OPENROUTER: "https://openrouter.ai/api/v1",
    LLMProviderName.MISTRAL: "https://api.mistral.ai/v1",
    LLMProviderName.OPENAI: "https://api.openai.com/v1",
    LLMProviderName.OLLAMA: "http://localhost:11434",
}


def get_prices_per_mtok(settings: Settings, model_id: str) -> tuple[float, float]:
    known_input, known_output = KNOWN_PRICES_PER_MTOK_USD.get(model_id, (0.0, 0.0))
    return (
        settings.llm_price_input_per_mtok_usd
        if settings.llm_price_input_per_mtok_usd is not None
        else known_input,
        settings.llm_price_output_per_mtok_usd
        if settings.llm_price_output_per_mtok_usd is not None
        else known_output,
    )


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Never raises: a misconfigured provider fails per call, so the API stays up and reports a
    technical status instead of crashing (CONCEPT §7.4)."""
    name = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS.get(name)
    key = settings.llm_api_key
    if name is LLMProviderName.OPENROUTER and settings.openrouter_api_key:
        key = settings.openrouter_api_key
    api_key = key.get_secret_value() if key else None
    base_url = settings.llm_base_url or DEFAULT_BASE_URLS.get(name, "")
    if name not in (LLMProviderName.MOCK, LLMProviderName.FAILING) and not model:
        return FailingLLMProvider(
            error=LLMConfigError(f"LLM_MODEL must be set for LLM_PROVIDER={name}"),
            reported_model_id=f"{name}/unset",
        )
    match name:
        case LLMProviderName.MOCK:
            return MockLLMProvider(
                responder=get_offline_responder(), reported_model_id=OFFLINE_MODEL_ID
            )
        case LLMProviderName.FAILING:
            return FailingLLMProvider()
        case LLMProviderName.OPENROUTER:
            provider_preferences: dict = {"require_parameters": True}
            if settings.openrouter_deny_data_collection:
                provider_preferences["data_collection"] = "deny"
            return ChatCompletionsProvider(
                provider_name=name.value,
                model=str(model),
                api_key=api_key,
                base_url=base_url,
                timeout_s=settings.llm_timeout_s,
                use_json_schema=True,
                extra_body={"provider": provider_preferences},
            )
        case LLMProviderName.MISTRAL | LLMProviderName.OPENAI:
            return ChatCompletionsProvider(
                provider_name=name.value,
                model=str(model),
                api_key=api_key,
                base_url=base_url,
                timeout_s=settings.llm_timeout_s,
            )
        case LLMProviderName.ANTHROPIC:
            return AnthropicProvider(
                model=str(model), api_key=api_key, timeout_s=settings.llm_timeout_s
            )
        case LLMProviderName.OLLAMA:
            return OllamaProvider(
                model=str(model), base_url=base_url, timeout_s=settings.llm_timeout_s
            )

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data"


class LLMProviderName(StrEnum):
    MOCK = "mock"
    FAILING = "failing"
    OPENROUTER = "openrouter"
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class EmbeddingProviderName(StrEnum):
    HASHING = "hashing"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class OCRProviderName(StrEnum):
    NONE = "none"
    TESSERACT = "tesseract"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: LLMProviderName = LLMProviderName.OPENROUTER
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    openrouter_deny_data_collection: bool = True
    llm_base_url: str | None = None
    llm_timeout_s: float = 25.0
    llm_price_input_per_mtok_usd: float | None = None
    llm_price_output_per_mtok_usd: float | None = None

    embedding_provider: EmbeddingProviderName = EmbeddingProviderName.HASHING
    embedding_model: str = "intfloat/multilingual-e5-base"

    ocr_provider: OCRProviderName = OCRProviderName.TESSERACT
    ocr_languages: str = "pol+eng"

    db_path: Path = DATA_DIR / "prawdowid.sqlite"
    corpus_path: Path = DATA_DIR / "corpus.sqlite"
    sources_path: Path = DATA_DIR / "sources.yaml"
    incidents_dir: Path = DATA_DIR / "incidents"
    source_status_path: Path = DATA_DIR / "source_status.yaml"

    retention_days: int = 30
    max_claims: int = 5
    retrieval_top_k: int = 6
    retrieval_min_relevance: float = 0.30
    citation_min_similarity: float = 90.0
    archival_after_days: int = 365
    time_sensitive_archival_after_days: int = 7

    rate_limit_per_minute: int = 10
    rate_limit_per_day: int = 200

    fetch_timeout_s: float = 10.0
    fetch_max_bytes: int = 3_000_000
    fetch_user_agent: str = "PrawdowidBot/0.1 (+https://github.com/; source-based fact checking)"
    fetch_respect_robots: bool = True

    google_factcheck_api_key: SecretStr | None = None
    factcheck_publisher_allowlist: str = "Demagog,AFP Sprawdzam,AFP,Konkret24,OKO.press,FakeHunter"

    moderator_discord_webhook_url: SecretStr | None = None
    case_similarity_threshold: float = 0.85
    case_alert_after_repeats: int = 3

    admin_token: SecretStr | None = None
    public_web_base_url: str = "http://localhost:8000"
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()

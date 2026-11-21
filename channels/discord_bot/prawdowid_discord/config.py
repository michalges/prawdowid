from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(APP_ROOT / ".env", ".env"), extra="ignore", env_ignore_empty=True)

    discord_token: SecretStr
    prawdowid_api_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:5173"
    api_timeout_s: float = 90.0
    discord_guild_id: int | None = None
    """Optional: sync slash commands to one server instantly (global sync can take up to an hour)."""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

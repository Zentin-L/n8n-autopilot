"""Application configuration for the n8n AI agent."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings."""

    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_BASE_URL: str = "https://router.huggingface.co/v1"
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-3.3-70B-Instruct"
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE_SECONDS: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()

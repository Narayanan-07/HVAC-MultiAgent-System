"""
Application configuration.

This module centralizes environment-based configuration using Pydantic settings.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings loaded from environment variables and a local `.env` file.

    Notes:
    - API keys default to empty string so the server can start for health checks,
      but a startup warning is emitted if both LLM keys are absent.
    """

    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./hvac_system.db"
    REPORTS_DIR: str = "reports"
    DATA_DIR: str = "data"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# A module-level instance for convenience across the codebase.
settings = Settings()


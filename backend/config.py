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
    - `GEMINI_API_KEY` is optional by default so the API can start and serve
      endpoints like `/health` without requiring external API credentials.
    """

    GEMINI_API_KEY: str = "AIzaSyB3eYHP6r5vDcWba_4reFtpZbz_gOaeUvA"
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


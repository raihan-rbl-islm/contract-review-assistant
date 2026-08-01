"""
Application configuration via pydantic-settings.
All settings are loaded from environment variables (or .env file).
See Plan.md §18 for the expected env vars.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings, loaded from environment variables."""

    gemini_api_key: str = "your-key-here"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    cors_origin: str = "http://localhost:3000"
    log_level: str = "INFO"

    # Resolved path to the docs/problem Datasets directory (the actual dataset location)
    # This is derived at import time, not from an env var.
    docs_dir: Path = Path(__file__).resolve().parent.parent.parent / "docs" / "problem Datasets"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

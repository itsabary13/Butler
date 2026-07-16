"""Loads all configuration from environment variables (.env in this directory).

Never hardcode secrets here — every value below is read from the environment,
and .env is gitignored. See .env.example for the full list of names.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-5"

    # OpenAI (STT + TTS)
    openai_api_key: str

    # Telegram
    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_owner_chat_id: str

    # Google Calendar OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_refresh_token: str = ""
    primary_calendar_id: str = "primary"

    # Wiki / document access
    wiki_repo_path: str = "../memory-module/wiki"
    wiki_repo_url: str = ""
    docs_repo_path: str = "../document-module/files"
    docs_repo_url: str = ""
    wiki_git_token: str = ""

    # Session store
    session_ttl_minutes: int = 30
    session_max_turns: int = 8


settings = Settings()

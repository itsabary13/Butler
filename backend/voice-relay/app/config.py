"""Loads all configuration from environment variables (.env in this directory).

Never hardcode secrets here — every value below is read from the environment,
and .env is gitignored. See .env.example for the full list of names.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("voice_relay.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Claude Code (headless, billed against the Claude Pro/Max subscription's
    # usage allowance via CLAUDE_CODE_OAUTH_TOKEN — no API key, no pay-per-token
    # billing; see .env.example and docs/architecture/voice-relay.md's v2 addendum)
    claude_binary: str = "claude"
    claude_code_model: str = ""

    # Local speech models (faster-whisper STT + Piper TTS — no account, no billing)
    whisper_model_size: str = "small"
    piper_voice_model_path: str
    piper_voice_config_path: str = ""

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

    # Proactive notifications (v1.6 addendum, docs/architecture/voice-relay.md)
    # — off by default; deploying this code changes nothing until explicitly
    # enabled. All other values are safe, conservative defaults, tunable
    # without a code change.
    proactive_enabled: bool = False
    proactive_hour_local: int = 8
    local_timezone: str = "UTC"
    proactive_lookahead_days: int = 7
    proactive_max_per_day: int = 3
    proactive_cooldown_days: int = 30
    quiet_hours_start: int = 8
    quiet_hours_end: int = 21


settings = Settings()


def local_now() -> datetime:
    """Current time in settings.local_timezone, falling back to UTC if the
    configured zone name is invalid. Shared by anything that needs to
    reason in the user's own local time rather than UTC — app/proactive.py's
    scheduling/quiet-hours math, and app/claude_code_client.py's system
    prompt (v1.9 fix: the model previously only ever saw UTC, with no way
    to know the user's actual local time, causing "today"/"tomorrow"/a
    stated clock time to be interpreted in the wrong timezone). requirements.txt
    pins the `tzdata` PyPI package specifically so this works regardless of
    whether the base image's OS ships the IANA database (python:3.12-slim
    doesn't by default) — zoneinfo falls back to it automatically."""
    try:
        tz = ZoneInfo(settings.local_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("invalid LOCAL_TIMEZONE %r, falling back to UTC", settings.local_timezone)
        tz = timezone.utc
    return datetime.now(tz)

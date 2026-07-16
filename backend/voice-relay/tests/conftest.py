"""Sets dummy required config values before any `app` module is imported,
so tests never need a real .env / real secrets. Fictional placeholder
values only, per this project's standing rule against real data even in
throwaway contexts.
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("TELEGRAM_OWNER_CHAT_ID", "12345")

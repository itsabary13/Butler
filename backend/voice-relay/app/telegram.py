"""Telegram Bot API surface: receive voice-message webhooks, send voice
replies. Narrow enough (one webhook, getFile, sendVoice/sendAudio) that
raw httpx calls are simpler than a full bot-dispatch framework
(docs/architecture/voice-relay.md).

One-time setup, after the app is running and publicly reachable
(e.g. via ngrok for local dev):

    curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \\
         -d "url=https://<public-host>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>" \\
         -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"

Note: TELEGRAM_WEBHOOK_SECRET is used both as the URL path segment and as
Telegram's own secret_token header value — two independent checks against
the same configured secret, per docs/api/voice-relay.md.
"""

import httpx

from app.config import settings

API_BASE = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


def verify_webhook_secret(secret_from_path: str, secret_token_header: str | None) -> bool:
    """Checks only the two secret values — doesn't require a parsed update,
    so this can (and should) run before any request body is even
    inspected, for every request regardless of payload shape."""
    if secret_from_path != settings.telegram_webhook_secret:
        return False
    if secret_token_header != settings.telegram_webhook_secret:
        return False
    return True


def is_authorized(secret_from_path: str, secret_token_header: str | None, chat_id: str) -> bool:
    if not verify_webhook_secret(secret_from_path, secret_token_header):
        return False
    if str(chat_id) != str(settings.telegram_owner_chat_id):
        return False
    return True


def extract_voice_message(update: dict) -> dict | None:
    """Returns {chat_id, file_id, duration} if this update is a voice
    message from a chat, else None (e.g. a non-voice message, or an update
    type we don't handle). duration is Telegram's own reported length in
    whole seconds."""
    message = update.get("message")
    if not message or "voice" not in message:
        return None
    return {
        "chat_id": message["chat"]["id"],
        "file_id": message["voice"]["file_id"],
        "duration": message["voice"].get("duration", 0),
    }


async def download_voice(file_id: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        file_info = await client.get(f"{API_BASE}/getFile", params={"file_id": file_id})
        file_info.raise_for_status()
        file_path = file_info.json()["result"]["file_path"]

        file_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
        audio = await client.get(file_url)
        audio.raise_for_status()
        return audio.content


async def send_voice_reply(chat_id: str, audio_bytes: bytes) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{API_BASE}/sendVoice",
            data={"chat_id": chat_id},
            files={"voice": ("reply.ogg", audio_bytes, "audio/ogg")},
        )
        if response.status_code != 200:
            # Fall back to sendAudio if the voice-bubble format is rejected
            # (docs/architecture/voice-relay.md's codec risk note)
            fallback = await client.post(
                f"{API_BASE}/sendAudio",
                data={"chat_id": chat_id},
                files={"audio": ("reply.ogg", audio_bytes, "audio/ogg")},
            )
            fallback.raise_for_status()


async def send_text_reply(chat_id: str, text: str) -> None:
    """Used only for error reporting when the voice pipeline itself fails
    partway — never the primary reply path (FR-5, voice-conversation.md
    requires a spoken reply for every processed message)."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{API_BASE}/sendMessage",
            data={"chat_id": chat_id, "text": text},
        )

"""FastAPI app: POST /telegram/webhook/{secret}, GET /health.
See docs/api/voice-relay.md for the full API design.
"""

import logging

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from app import stt, telegram, tts, wiki_sync
from app.anthropic_client import get_reply
from app.config import settings
from app.tools import document_tools, session_store, wiki_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_relay.main")

app = FastAPI(title="Butler Voice Relay")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Check the secret first, for every request, regardless of payload shape —
    # doing this only after branching on message type would let an
    # unauthenticated caller distinguish "voice vs. non-voice" behavior
    # without ever presenting the right secret.
    if not telegram.verify_webhook_secret(secret, x_telegram_bot_api_secret_token):
        logger.warning("rejected webhook call with invalid secret")
        return JSONResponse({}, status_code=401)

    update = await request.json()

    voice = telegram.extract_voice_message(update)
    if voice is None:
        # Not a voice message (text, sticker, etc.) — silently ignore for v1;
        # voice is the only supported input per specs/epics/voice-relay.md.
        return JSONResponse({})

    chat_id = voice["chat_id"]

    if str(chat_id) != str(settings.telegram_owner_chat_id):
        # Right secret, wrong sender — still dropped without a reply
        # (docs/api/voice-relay.md).
        logger.warning("rejected webhook call from non-owner chat_id=%s", chat_id)
        return JSONResponse({}, status_code=401)

    try:
        await _handle_voice_message(chat_id, voice["file_id"])
    except Exception:
        logger.exception("failed to process voice message for chat_id=%s", chat_id)
        try:
            await telegram.send_text_reply(
                chat_id, "Sorry, something went wrong processing that — please try again."
            )
        except Exception:
            logger.exception("failed to even send the error reply")

    return JSONResponse({})


async def _handle_voice_message(chat_id: str, file_id: str) -> None:
    wiki_dir = wiki_tools.wiki_dir()
    docs_dir = document_tools.docs_dir()
    wiki_sync.sync_before(wiki_dir)
    wiki_sync.sync_before(docs_dir)

    audio_bytes = await telegram.download_voice(file_id)
    user_text = stt.transcribe(audio_bytes)
    logger.info("chat_id=%s transcribed: %s", chat_id, user_text)

    history = session_store.get_history(str(chat_id))
    reply_text = get_reply(user_text, history)

    session_store.append_turn(str(chat_id), "user", user_text)
    session_store.append_turn(str(chat_id), "assistant", reply_text)

    reply_audio = tts.synthesize(reply_text)
    await telegram.send_voice_reply(chat_id, reply_audio)

    wiki_sync.sync_after(wiki_dir, f"voice-relay: update from chat {chat_id}")
    wiki_sync.sync_after(docs_dir, f"voice-relay: update from chat {chat_id}")

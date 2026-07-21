"""FastAPI app: POST /telegram/webhook/{secret}, GET /health.
See docs/api/voice-relay.md for the full API design.
"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import BackgroundTasks, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from app import proactive, stt, telegram, tts, wiki_sync
from app.claude_code_client import enrich_document, get_reply
from app.config import settings
from app.tools import document_tools, wiki_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_relay.main")

MIN_VOICE_DURATION_SECONDS = 1


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The daily proactive scan (app/proactive.py, v1.6 addendum) — an
    # internal-only timer, never a network-reachable trigger, since its
    # whole effect is "message the user unprompted." Runs in this same
    # single process (Dockerfile's CMD has no --workers); a second worker
    # would double-fire the job, so that constraint must hold.
    scheduler = AsyncIOScheduler()
    proactive.register_scheduler(scheduler)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Butler Voice Relay", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    secret: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Check the secret first, for every request, regardless of payload shape —
    # doing this only after branching on message type would let an
    # unauthenticated caller distinguish "which message types this endpoint
    # handles" without ever presenting the right secret.
    if not telegram.verify_webhook_secret(secret, x_telegram_bot_api_secret_token):
        logger.warning("rejected webhook call with invalid secret")
        return JSONResponse({}, status_code=401)

    update = await request.json()

    voice = telegram.extract_voice_message(update)
    document = telegram.extract_document_message(update) if voice is None else None
    photo = telegram.extract_photo_message(update) if voice is None and document is None else None
    text = (
        telegram.extract_text_message(update)
        if voice is None and document is None and photo is None
        else None
    )

    payload = voice or document or photo or text
    if payload is None:
        # Not a message type we act on (sticker, edited_message, etc.) —
        # silently ignore, same as before: once the secret above is
        # confirmed authentic, there's nothing to authorize here since
        # nothing is going to be processed either way.
        return JSONResponse({})

    chat_id = payload["chat_id"]

    if str(chat_id) != str(settings.telegram_owner_chat_id):
        # Right secret, wrong sender — still dropped without a reply
        # (docs/api/voice-relay.md).
        logger.warning("rejected webhook call from non-owner chat_id=%s", chat_id)
        return JSONResponse({}, status_code=401)

    # Ack Telegram immediately and do the real work in the background — the
    # full pipeline (STT/document save + the claude subprocess call + TTS)
    # can easily run past Telegram's webhook response window, and Telegram
    # re-delivers the same update (reprocessing it from scratch) if it
    # doesn't see a fast 200. The actual reply goes out via a separate
    # send call regardless, so the webhook response body was never carrying it.
    if voice is not None:
        if voice["duration"] < MIN_VOICE_DURATION_SECONDS:
            # Almost always an accidental tap, not real speech — an empty/
            # near-empty transcript just reaches claude with nothing to say.
            logger.info(
                "dropped voice message under %ss (chat_id=%s, duration=%ss)",
                MIN_VOICE_DURATION_SECONDS, chat_id, voice["duration"],
            )
            return JSONResponse({})
        background_tasks.add_task(_process_voice_message, chat_id, voice["file_id"])
    elif document is not None:
        background_tasks.add_task(
            _process_document_message, chat_id, document["file_id"], document["filename"], document["caption"]
        )
    elif photo is not None:
        # A photo has no original filename (unlike a document upload) — the
        # same save_document/document_tools.py convention just needs one to
        # derive a slug/extension from, so a generic default stands in.
        background_tasks.add_task(
            _process_document_message, chat_id, photo["file_id"], "photo.jpg", photo["caption"]
        )
    else:
        background_tasks.add_task(_process_text_message, chat_id, text["text"])

    return JSONResponse({})


async def _process_voice_message(chat_id: str, file_id: str) -> None:
    try:
        await _handle_voice_message(chat_id, file_id)
    except Exception:
        logger.exception("failed to process voice message for chat_id=%s", chat_id)
        try:
            await telegram.send_text_reply(
                chat_id, "Sorry, something went wrong processing that — please try again."
            )
        except Exception:
            logger.exception("failed to even send the error reply")


async def _handle_voice_message(chat_id: str, file_id: str) -> None:
    wiki_dir = wiki_tools.wiki_dir()
    docs_dir = document_tools.docs_dir()
    wiki_sync.sync_before(wiki_dir)
    wiki_sync.sync_before(docs_dir)

    audio_bytes = await telegram.download_file(file_id)
    user_text = stt.transcribe(audio_bytes)
    logger.info("chat_id=%s transcribed: %s", chat_id, user_text)

    reply_text = get_reply(str(chat_id), user_text)

    reply_audio = tts.synthesize(reply_text)
    await telegram.send_voice_reply(chat_id, reply_audio)

    wiki_sync.sync_after(wiki_dir, f"voice-relay: update from chat {chat_id}")
    wiki_sync.sync_after(docs_dir, f"voice-relay: update from chat {chat_id}")


async def _process_text_message(chat_id: str, text: str) -> None:
    try:
        await _handle_text_message(chat_id, text)
    except Exception:
        logger.exception("failed to process text message for chat_id=%s", chat_id)
        try:
            await telegram.send_text_reply(
                chat_id, "Sorry, something went wrong processing that — please try again."
            )
        except Exception:
            logger.exception("failed to even send the error reply")


async def _handle_text_message(chat_id: str, text: str) -> None:
    """Same 'brain' as voice (app.claude_code_client.get_reply, same tools,
    same session continuity) — just typed instead of spoken, so there's no
    STT/TTS step, and the reply goes back as text instead of a voice note."""
    wiki_dir = wiki_tools.wiki_dir()
    docs_dir = document_tools.docs_dir()
    wiki_sync.sync_before(wiki_dir)
    wiki_sync.sync_before(docs_dir)

    reply_text = get_reply(str(chat_id), text)
    await telegram.send_text_reply(chat_id, reply_text)

    wiki_sync.sync_after(wiki_dir, f"voice-relay: update from chat {chat_id}")
    wiki_sync.sync_after(docs_dir, f"voice-relay: update from chat {chat_id}")


async def _process_document_message(chat_id: str, file_id: str, filename: str, caption: str | None) -> None:
    try:
        await _handle_document_message(chat_id, file_id, filename, caption)
    except Exception:
        logger.exception("failed to process document message for chat_id=%s", chat_id)
        try:
            await telegram.send_text_reply(
                chat_id, "Sorry, something went wrong saving that document — please try again."
            )
        except Exception:
            logger.exception("failed to even send the error reply")


async def _handle_document_message(chat_id: str, file_id: str, filename: str, caption: str | None) -> None:
    """Two-phase save: a deterministic placeholder save
    (app.tools.document_tools.save_document — file bytes can't reasonably
    flow through an MCP tool-call's JSON arguments, so there's nothing for
    claude to do for this part), then claude_code_client.enrich_document
    reads the actual saved file and renames/categorizes it + saves anything
    worth remembering (v1.5 addendum, docs/architecture/voice-relay.md)."""
    docs_dir = document_tools.docs_dir()
    wiki_dir = wiki_tools.wiki_dir()
    wiki_sync.sync_before(docs_dir)
    wiki_sync.sync_before(wiki_dir)

    file_bytes = await telegram.download_file(file_id)
    result = document_tools.save_document(filename, file_bytes, title=caption)

    summary = enrich_document(result["path"], result["slug"], result["title"], caption)

    wiki_sync.sync_after(docs_dir, f"voice-relay: document upload from chat {chat_id}")
    wiki_sync.sync_after(wiki_dir, f"voice-relay: document upload from chat {chat_id}")

    await telegram.send_text_reply(chat_id, summary)

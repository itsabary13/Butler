# Voice Relay

The one real server process in this repo. Everything else in Butler runs as Claude Code skills inside a Claude Code session — no server, no database. Genuine voice (speak from anywhere, hear a response) needs real speech-to-text/text-to-speech integration, and there's no way to wire that up without some server-side piece, so this is that piece.

See `specs/epics/voice-relay.md` for the full spec, `docs/architecture/voice-relay.md` for the architecture, and the plan this was built from for the reasoning behind each choice.

## What it is

A small FastAPI service that:
1. Receives voice messages via a Telegram bot webhook.
2. Transcribes them (OpenAI STT).
3. Answers using its own direct Anthropic API tool-use loop — reading the same wiki files `remember`/`recall` use (`docs/db/memory-module.md`), not by invoking Claude Code skills (which only run inside a Claude Code session).
4. Can create Google Calendar events directly (its own OAuth credentials, not the Claude Code connector).
5. Replies with synthesized speech (OpenAI TTS) back through Telegram.

## Phase 1 vs. Phase 2

Phase 1 (this): prove the mechanism works — run locally with a tunnel (e.g. ngrok) for the Telegram webhook. Not 24/7 hosted yet.
Phase 2 (later, not built yet): deploy this same code (the `Dockerfile` already exists for this) to a VPS for true always-on availability.

## Setup

1. `cp .env.example .env` and fill in real values — see comments in that file for what each one is and where to get it.
2. `pip install -r requirements.txt`
3. One-time Google Calendar OAuth consent: `python scripts/google_oauth_setup.py` (see that script's own comments — do this before running the app for the first time).
4. `uvicorn app.main:app --reload --port 8000`
5. Expose it publicly for Telegram's webhook (e.g. `ngrok http 8000`), then register the webhook URL with Telegram (see `app/telegram.py`'s module docstring for the exact `setWebhook` call).

## Important

- This service is billed separately from your Claude Code/claude.ai subscription — it makes its own Anthropic API calls, plus OpenAI and Google Calendar API usage.
- Never put real personal data into anything committed here — same rule as the rest of this repo (`docs/workflow.md`). `.env` and `data/` are gitignored for exactly this reason.
- Single-user only: the Telegram webhook only processes messages from `TELEGRAM_OWNER_CHAT_ID`; everything else is dropped.

# Voice Relay

The one real server process in this repo. Everything else in Butler runs as Claude Code skills inside a Claude Code session — no server, no database. Genuine voice (speak from anywhere, hear a response) needs real speech-to-text/text-to-speech integration, and there's no way to wire that up without some server-side piece, so this is that piece.

See `specs/epics/voice-relay.md` for the full spec, `docs/architecture/voice-relay.md` for the architecture, and the plan this was built from for the reasoning behind each choice.

## What it is

A small FastAPI service that:
1. Receives voice messages via a Telegram bot webhook.
2. Transcribes them locally (faster-whisper — no account, no per-request billing).
3. Answers using its own direct Anthropic API tool-use loop — reading the same wiki files `remember`/`recall` use (`docs/db/memory-module.md`), not by invoking Claude Code skills (which only run inside a Claude Code session).
4. Can create Google Calendar events directly (its own OAuth credentials, not the Claude Code connector).
5. Replies with synthesized speech (Piper, also local — see `docs/architecture/voice-relay.md`'s v1.1 addendum) back through Telegram.

## Phase 1 vs. Phase 2

Phase 1: prove the mechanism works — run locally with a tunnel (e.g. ngrok) for the Telegram webhook. Not 24/7 hosted.
Phase 2 (underway — see `DEPLOY.md`): the same code, deployed to a DigitalOcean droplet via Docker Compose + Caddy for true always-on availability. Moved to Phase 2 sooner than originally planned because a corporate network's proxy policy blocked `api.telegram.org` outright, which would have blocked Phase 1 testing entirely from that machine — a VPS with its own unrestricted connection sidesteps that permanently. Follow `DEPLOY.md` for the concrete runbook.

## Setup (local/Phase 1)

1. `cp .env.example .env` and fill in real values — see comments in that file for what each one is and where to get it.
2. `pip install -r requirements.txt`
3. Install `ffmpeg` and make sure it's on your `PATH` (needed to convert Piper's WAV output to Opus/OGG for Telegram voice notes; already included in the Dockerfile for containerized runs). On Windows: `winget install --id Gyan.FFmpeg -e`.
4. One-time Piper voice download: `python scripts/download_piper_voice.py` (defaults to `en_US-lessac-medium`, ~65MB, cached under `models/` — gitignored). faster-whisper's model downloads/caches automatically the first time it's used, no separate step needed.
5. One-time Google Calendar OAuth consent: `python scripts/google_oauth_setup.py` (see that script's own comments — do this before running the app for the first time).
6. `uvicorn app.main:app --reload --port 8000`
7. Expose it publicly for Telegram's webhook (e.g. `ngrok http 8000`), then register the webhook URL with Telegram (see `app/telegram.py`'s module docstring for the exact `setWebhook` call).

## Important

- This service is billed separately from your Claude Code/claude.ai subscription — it makes its own Anthropic API calls, plus Google Calendar API usage. Speech-to-text and text-to-speech are fully local (faster-whisper, Piper) — no OpenAI or other speech-provider account needed, and no per-request billing for either (see `docs/architecture/voice-relay.md`'s v1.1 addendum).
- On a machine behind a corporate SSL-intercepting proxy, the very first `faster-whisper`/Piper model download may fail with a certificate error even though your browser trusts the site fine — `pip install pip-system-certs` fixes this by making Python's HTTPS libraries trust the same certificate store Windows already does. Only ever needed once, for the download itself.
- Never put real personal data into anything committed here — same rule as the rest of this repo (`docs/workflow.md`). `.env`, `data/`, and `models/` are gitignored for exactly this reason (`models/` holds large downloaded binaries, not source).
- Single-user only: the Telegram webhook only processes messages from `TELEGRAM_OWNER_CHAT_ID`; everything else is dropped.

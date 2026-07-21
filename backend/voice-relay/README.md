# Voice Relay

The one real server process in this repo. Everything else in Butler runs as Claude Code skills inside a Claude Code session — no server, no database. Genuine voice (speak from anywhere, hear a response) needs real speech-to-text/text-to-speech integration, and there's no way to wire that up without some server-side piece, so this is that piece.

See `specs/epics/voice-relay.md` for the full spec, `docs/architecture/voice-relay.md` for the architecture, and the plan this was built from for the reasoning behind each choice.

## What it is

A small FastAPI service that handles three Telegram message types (voice, text, document — v1.4 addendum, `specs/epics/voice-relay.md`), plus one thing it can do entirely on its own:

- **Voice**: transcribed locally (faster-whisper — no account, no per-request billing; restricted to English/Hebrew/Russian, `app/stt.py`), answered, then replied to with synthesized speech (Piper, also local — see `docs/architecture/voice-relay.md`'s v1.1 addendum).
- **Text**: answered the same way as voice, minus STT/TTS — same "brain," same tools, same conversation continuity, just typed instead of spoken, replied to with text.
- **Document or photo**: saved into the same file+metadata convention the `add-document` skill uses (`docs/db/document-module.md`), covering both of Telegram's upload shapes — a "File" attachment, and the ordinary Photo picker/camera button (compressed, no filename of its own). The initial save is deterministic, not LLM-driven (file bytes can't reasonably flow through an MCP tool call) — but a second pass then actually reads the content and auto-names/categorizes it, and saves anything worth remembering into the wiki so it's answerable later ("what does my ticket say"), not just findable by title (v1.5 addendum).
- **Proactive notifications** (v1.6 addendum, off by default — `PROACTIVE_ENABLED`): once a day, checks for genuinely actionable items (an imminent calendar appointment, a clearly overdue recurring pattern like a checkup) and messages you unprompted if it finds one. This is the one thing in the whole relay that initiates contact rather than reacting to a message, so it's built with an explicit safety split: the model can only *propose* a notification, never send one — a deterministic Python gate (dedup, a daily cap, quiet hours) decides what, if anything, actually goes out. See `docs/architecture/voice-relay.md`'s v5 addendum for the full design.

Answering (voice and text) goes through a headless `claude` CLI call, billed against your Claude Pro/Max subscription's usage allowance rather than a pay-per-token API key (see `docs/architecture/voice-relay.md`'s v2 addendum) — reading the same wiki files `remember`/`recall` use (`docs/db/memory-module.md`) through a local MCP server (`app/mcp_server.py`), not by invoking Claude Code skills directly (which only run inside an interactive Claude Code session). It can also create/list Google Calendar events directly (its own OAuth credentials, not the Claude Code connector).

## Phase 1 vs. Phase 2

Phase 1: prove the mechanism works — run locally with a tunnel (e.g. ngrok) for the Telegram webhook. Not 24/7 hosted.
Phase 2 (underway — see `DEPLOY.md`): the same code, deployed to a DigitalOcean droplet via Docker Compose + Caddy for true always-on availability. Moved to Phase 2 sooner than originally planned because a corporate network's proxy policy blocked `api.telegram.org` outright, which would have blocked Phase 1 testing entirely from that machine — a VPS with its own unrestricted connection sidesteps that permanently. Follow `DEPLOY.md` for the concrete runbook.

## Setup (local/Phase 1)

1. `cp .env.example .env` and fill in real values — see comments in that file for what each one is and where to get it.
2. `pip install -r requirements.txt`
3. Install the `claude` CLI (`npm install -g @anthropic-ai/claude-code`) and run `claude setup-token` once, logged into your Claude.ai account, to generate `CLAUDE_CODE_OAUTH_TOKEN` for `.env` (see `docs/architecture/voice-relay.md`'s v2 addendum).
4. Install `ffmpeg` and make sure it's on your `PATH` (needed to convert Piper's WAV output to Opus/OGG for Telegram voice notes; already included in the Dockerfile for containerized runs). On Windows: `winget install --id Gyan.FFmpeg -e`.
5. One-time Piper voice download: `python scripts/download_piper_voice.py` (defaults to `en_US-lessac-medium`, ~65MB, cached under `models/` — gitignored). faster-whisper's model downloads/caches automatically the first time it's used, no separate step needed.
6. One-time Google Calendar OAuth consent: `python scripts/google_oauth_setup.py` (see that script's own comments — do this before running the app for the first time).
7. `uvicorn app.main:app --reload --port 8000`
8. Expose it publicly for Telegram's webhook (e.g. `ngrok http 8000`), then register the webhook URL with Telegram (see `app/telegram.py`'s module docstring for the exact `setWebhook` call).
9. (Optional) Proactive notifications ship disabled — leave `PROACTIVE_ENABLED=false` until you've done the manual live-verification pass in `DEPLOY.md`, then flip it on and restart.

## Important

- Billed against your existing Claude Pro/Max subscription's usage allowance, not a separate pay-per-token Anthropic API key (see `docs/architecture/voice-relay.md`'s v2 addendum) — plus Google Calendar API usage (free tier). Speech-to-text and text-to-speech are fully local (faster-whisper, Piper) — no OpenAI or other speech-provider account needed, and no per-request billing for either (see `docs/architecture/voice-relay.md`'s v1.1 addendum). Pro/Max usage is subject to that plan's normal rate limits (weekly caps), unlike unmetered pay-per-token billing.
- On a machine behind a corporate SSL-intercepting proxy, the very first `faster-whisper`/Piper model download may fail with a certificate error even though your browser trusts the site fine — `pip install pip-system-certs` fixes this by making Python's HTTPS libraries trust the same certificate store Windows already does. Only ever needed once, for the download itself.
- Never put real personal data into anything committed here — same rule as the rest of this repo (`docs/workflow.md`). `.env`, `data/`, and `models/` are gitignored for exactly this reason (`models/` holds large downloaded binaries, not source).
- Single-user only: the Telegram webhook only processes messages from `TELEGRAM_OWNER_CHAT_ID`; everything else is dropped.
- Proactive notifications (if enabled) run one extra `claude` invocation per day, on top of reactive usage — still against the same Pro/Max subscription allowance, no separate billing, just worth knowing it's additional daily draw on that same rate-limited quota.

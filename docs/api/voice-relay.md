# API Design: Voice Relay

Unlike Memory/Document (both N/A — no server), this epic genuinely exposes a network API, since it's the one server process in this repo.

## `POST /telegram/webhook/{secret}`

Telegram's webhook target — receives every update sent to the bot.

- **Path parameter**: `{secret}` — a random, hard-to-guess path segment (not the sole auth mechanism; see below).
- **Auth**: request MUST carry Telegram's `X-Telegram-Bot-Api-Secret-Token` header matching `TELEGRAM_WEBHOOK_SECRET`, AND the update's `message.chat.id` MUST equal `TELEGRAM_OWNER_CHAT_ID`. Either check failing → `401`, request dropped, nothing processed, no reply sent.
- **Request body**: Telegram's own webhook update JSON (voice messages arrive with a `message.voice.file_id`).
- **Response**: `200 {}` immediately after acknowledging receipt is preferable to Telegram, with the actual transcribe → reason → reply pipeline running before responding (v1: synchronous, single request lifecycle — no queue/worker yet, acceptable at single-user volume; a Phase-2-era concern if latency becomes an issue).
- **Errors**: any downstream failure (STT, Anthropic, TTS, Telegram send) is caught, logged, and — where possible — reported back to the user as a spoken "something went wrong" reply rather than a silent drop, except for the two auth failures above, which are silently dropped by design (don't reveal to an unauthenticated caller whether the endpoint exists).

## `GET /health`

- **Auth**: none (used for basic liveness checks, e.g. by a future Phase 2 deployment's health probe).
- **Response**: `200 {"status": "ok"}` if the process is up. Does not verify downstream provider connectivity (Anthropic/Google/Telegram, or that the local STT/TTS models are loaded) — a deliberately minimal liveness check, not a full readiness check.

## Explicitly out of scope

Any endpoint for a different transport (a phone-call webhook, a web UI, a WhatsApp webhook) — Telegram is the only transport for v1. No authenticated end-user-facing API beyond the webhook itself (no JWT/OAuth token issuance) — single-user, allowlist-based, per `docs/architecture/voice-relay.md`.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `database-designer` — the session store needs real (if minimal) schema design.

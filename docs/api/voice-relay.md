# API Design: Voice Relay

Unlike Memory/Document (both N/A — no server), this epic genuinely exposes a network API, since it's the one server process in this repo.

## `POST /telegram/webhook/{secret}`

Telegram's webhook target — receives every update sent to the bot. Handles four message types (v1.4 addendum, `specs/epics/voice-relay.md`): voice, plain text, document uploads, and photo uploads (Telegram sends these as two distinct types depending on whether the sender used "File" or the ordinary Photo picker — both are handled, the latter routed through the same document-save path with a synthesized filename). Any other type (sticker, edited_message, etc.) is silently accepted and ignored — there's nothing to authorize or process either way.

- **Path parameter**: `{secret}` — a random, hard-to-guess path segment (not the sole auth mechanism; see below).
- **Auth**: request MUST carry Telegram's `X-Telegram-Bot-Api-Secret-Token` header matching `TELEGRAM_WEBHOOK_SECRET`, AND (for voice/text/document messages specifically) the update's `message.chat.id` MUST equal `TELEGRAM_OWNER_CHAT_ID`. Either check failing → `401`, request dropped, nothing processed, no reply sent.
- **Request body**: Telegram's own webhook update JSON — `message.voice.file_id`/`.duration`, `message.document.file_id`/`.file_name` + `message.caption`, `message.photo` (list, highest-resolution entry used) + `message.caption`, or `message.text`, depending on type. A voice message under 1 second (`MIN_VOICE_DURATION_SECONDS`, `app/main.py`) is dropped silently, same treatment as an unhandled message type — almost always an accidental tap, and an empty/near-empty transcript otherwise just reaches `claude` with nothing to say.
- **Response**: `200 {}` returned immediately, before the transcribe → reason → reply (or document-save) pipeline runs. The original v1 design ran that pipeline synchronously before responding; live testing showed the full pipeline (local STT + the headless `claude` call + local TTS) routinely exceeds Telegram's webhook response window, so Telegram re-delivered the same update repeatedly, reprocessing it from scratch each time. Fixed by handing the pipeline to FastAPI's `BackgroundTasks` (runs after the response is sent, same process, no separate queue/worker — still appropriate at single-user volume) instead of awaiting it in the handler.
- **Errors**: any downstream failure (STT, `claude`, TTS, document save, Telegram send) is caught, logged, and — where possible — reported back to the user as a reply (spoken for voice, text otherwise) rather than a silent drop, except for the two auth failures above, which are silently dropped by design (don't reveal to an unauthenticated caller whether the endpoint exists).

## `GET /health`

- **Auth**: none (used for basic liveness checks, e.g. by a future Phase 2 deployment's health probe).
- **Response**: `200 {"status": "ok"}` if the process is up. Does not verify downstream provider connectivity (Anthropic/Google/Telegram, or that the local STT/TTS models are loaded) — a deliberately minimal liveness check, not a full readiness check.

## Proactive notifications (v1.6 addendum) — no new HTTP surface

The daily scan (`app/proactive.py`) is triggered by an in-process `AsyncIOScheduler` timer, not a request — deliberately no new route. Its whole effect is "message the user unprompted," so unlike everything else in this file, that trigger is never network-reachable at all; there's nothing here for this section to document beyond confirming the absence. Manual testing invokes it directly in-process (`docker compose exec voice-relay python -c "..."`, see `DEPLOY.md`), not over HTTP.

## Explicitly out of scope

Any endpoint for a different transport (a phone-call webhook, a web UI, a WhatsApp webhook) — Telegram is the only transport for v1. No authenticated end-user-facing API beyond the webhook itself (no JWT/OAuth token issuance) — single-user, allowlist-based, per `docs/architecture/voice-relay.md`. No HTTP-triggerable endpoint for the proactive scan, ever (see above) — an outbound-messaging trigger being network-reachable is a real risk this design avoids entirely rather than authenticating.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

This epic's API surface is complete through v1.6 (still just the webhook + health endpoint — the proactive scan deliberately adds none) — no further stage hand-off pending.

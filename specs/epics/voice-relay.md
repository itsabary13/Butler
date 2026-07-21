# Epic: Voice Relay

**Status: In progress** (Phase 1) — code, tests, review, and docs complete; live end-to-end verification against real credentials (Telegram bot, Anthropic/OpenAI keys, Google OAuth) is the one remaining step before this can be marked Shipped.

## Idea

Extend Butler so it's reachable and speakable-to from anywhere, not just from a Claude Code session at this machine. Originated from `input/always-on-voice-assistant-feature.md`, a generic voice-assistant spec that assumed an architecture (API gateway, database, Docker/K8s, JWT/OAuth, multi-provider LLM abstraction) that doesn't match Butler's actual design (Claude Code skills, no server, wiki-as-files). Scoped down through direct discussion into a phased plan.

## Why this is a new epic, not a fast-path increment

Per `docs/workflow.md`'s rule of thumb: this introduces a new component (a standalone server process — the first one in this repo), a new entity (a conversation Session), and new external integrations (Telegram, OpenAI STT/TTS, a direct Anthropic API client, a direct Google Calendar OAuth client) that don't reuse any existing Claude Code skill mechanism. That's the full-lifecycle bar, not the fast-path one.

## v1 scope — Phase 1: the voice relay itself

IN SCOPE:
- A new standalone service (`backend/voice-relay/`) reachable via a Telegram bot, accepting voice messages.
- Speech-to-text (OpenAI), a direct Anthropic API tool-use loop for answering (reading the same wiki files `remember`/`recall` use), text-to-speech (OpenAI) for the reply.
- Reading `backend/memory-module/wiki/` for context (own tool implementations: `list_wiki_pages`, `read_wiki_page`, following `[[wiki-link]]` references).
- Writing new memories/reminders (`save_memory`, `append_reminder`) — mirrors `remember`'s behavior, doesn't call it directly (can't — skills only run inside Claude Code sessions).
- Creating Google Calendar events directly (own OAuth client, not the Claude Code connector) — **create-only**, matching Memory's own precedent of deferring update/delete.
- Document lookup by metadata only (`find_document`) — no binary delivery over voice.
- Short-term, per-conversation session memory (a few turns, TTL-based) so follow-ups ("actually make it 2pm") resolve correctly.
- Single user only — a hard `chat_id` allowlist, not real multi-tenant auth.

OUT OF SCOPE for v1 (explicitly deferred):
- 24/7 hosting — this is Phase 1, proven locally/via tunnel; **Phase 2** (a separate, future epic) migrates this same code to a VPS.
- True real-time streaming voice with interruptions (a phone-call-style transport) — Telegram voice messages are turn-based, not a live stream.
- Multi-user auth.
- Calendar update/delete.
- Delivering document binaries over voice.
- Higher-end TTS providers (ElevenLabs, etc.) — revisit once voice personality quality actually matters.

## v1.1 addendum — local STT/TTS, no OpenAI dependency

While setting up real credentials for the live-verification step (Task 43), the user declined to create an OpenAI account — one more pay-per-usage subscription beyond Anthropic (already accepted, since Claude is the whole point of Butler) wasn't worth it. Replaced OpenAI's Whisper/TTS APIs with fully local, free, offline alternatives before any real OpenAI account was created: `faster-whisper` for STT, `piper` for TTS (user's choice over `edge-tts`/`pyttsx3`, prioritizing a genuinely offline dependency over marginally higher voice quality). See `docs/architecture/voice-relay.md`'s own v1.1 addendum for the full technical writeup. No change to scope, requirements, or any other module — `stt.transcribe()`/`tts.synthesize()` kept the same interface.

## Fixed constraints for v1

- **This is the one exception to "no server process."** Every other Butler capability stays inside Claude Code. This relay exists specifically because genuine voice has no path that avoids a server (confirmed: Claude Code's own `/voice` dictation is terminal-only and doesn't work over Remote Control; there's no text-to-speech anywhere in Claude's consumer products).
- **Reuses conventions, not code.** The relay does not and cannot call `remember`/`recall`/`sync-calendar` (those are Claude Code skills, inseparable from a Claude Code session). It reimplements the *behavior* against the same file conventions (`docs/db/memory-module.md`), the same relationship `sync-calendar` already has to `remember`.
- **Billed separately.** This relay makes its own direct Anthropic API calls (pay-per-token, separate from the Claude Code/claude.ai subscription), plus Google Calendar API usage. Speech-to-text/text-to-speech are local (v1.1 addendum above) and incur no per-request billing.
- **Same privacy rules as the rest of the repo.** No real personal data in anything committed to the public repo; secrets live only in `backend/voice-relay/.env` (gitignored).

## v1.2 addendum — Phase 2 underway

Phase 2 (VPS hosting) was explicitly deferred as "a separate, future epic" above, but moved up sooner than planned: setting up real Telegram credentials for Task 43's live verification surfaced that the machine being used sits behind a corporate proxy that blocks `api.telegram.org` outright, which would block the relay's Telegram traffic entirely, not just complicate testing. Rather than work around that per-network, moving straight to a DigitalOcean-hosted deployment resolves it permanently and was coming "soon" regardless. See `docs/architecture/voice-relay.md`'s v1.2 addendum and `backend/voice-relay/DEPLOY.md` for the deployment details. No scope, requirements, or domain/API/DB changes — same component, different hosting.

## v1.3 addendum — no pay-as-you-go API usage, subscription only

Constraint changed after Phase 2 was already live: VPS/domain cost stays accepted, but no pay-per-token Anthropic API billing at all — only the existing Claude Pro subscription. This supersedes the "Billed separately... pay-per-token" bullet in "Fixed constraints for v1" above. The relay now answers via headless Claude Code (`claude -p`, authenticated with `CLAUDE_CODE_OAUTH_TOKEN`) instead of a direct Anthropic API tool-use loop, drawing on the Pro plan's usage allowance instead of separate billing. Tools move from hand-rolled Anthropic tool-use schemas to a local MCP server exposing the same `app/tools/*` implementations. No scope change — same five tools, same wiki/calendar/document behavior. See `docs/architecture/voice-relay.md`'s v2 addendum for the full design and `docs/db/voice-relay.md`/`docs/domain/voice-relay.md` for the resulting `Session` schema change (a Claude Code `session_id` instead of a replayed transcript).

## Lifecycle Status

- [x] Epic / User Stories / Functional Requirements — requirements-analyst — `specs/stories/voice-relay/`
- [x] Architecture — architect — `docs/architecture/voice-relay.md`
- [x] Domain Model — domain-designer — `docs/domain/voice-relay.md`
- [x] API Design — api-designer — `docs/api/voice-relay.md`
- [x] Database Design — database-designer — `docs/db/voice-relay.md`
- [x] UI (N/A — Telegram is the interface) — frontend-developer — `docs/ui/voice-relay.md`
- [x] Implementation (backend) — backend-developer — `backend/voice-relay/`
- [x] Tests — test-engineer — `docs/tests/voice-relay.md`
- [x] Review — reviewer — `docs/reviews/voice-relay.md`
- [x] Documentation — technical-writer — `docs/features/voice-relay.md`

## MVP Roadmap Context

Not part of the original master plan's phase roadmap (`input/Jarvis-Claude-Code-Plan.md`) — this epic originates from a separate, later feature request (`input/always-on-voice-assistant-feature.md`), scoped down from its original over-broad form through direct discussion with the user.

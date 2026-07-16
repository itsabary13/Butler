# Architecture: Voice Relay

## Why this breaks the "no server" rule

Every other Butler capability (Memory, Documents) runs entirely inside a Claude Code session — no server, no database, no API. This epic is the deliberate, single exception: genuine voice (speak from anywhere, hear a reply) requires real speech-to-text/text-to-speech integration, and there's no way to wire that up without a server-side piece. Confirmed before designing this: Claude Code's own `/voice` dictation is terminal-only and doesn't work over Remote Control; there's no text-to-speech anywhere in Claude's consumer products.

## Module boundaries

1. **Telegram interface** (`app/telegram.py`) — receives voice messages via webhook, sends voice replies.
2. **Speech layer** (`app/stt.py`, `app/tts.py`) — OpenAI transcription and synthesis.
3. **Reasoning layer** (`app/anthropic_client.py`) — direct Anthropic API tool-use loop; this is the relay's "brain," standing in for what a Claude Code session + skills would normally do.
4. **Tools** (`app/tools/`) — `wiki_tools.py`, `calendar_tools.py`, `document_tools.py`, `session_store.py` — the relay's own implementations of memory/calendar/document access, since it cannot invoke Claude Code skills directly.
5. **Wiki/document sync** (`app/wiki_sync.py`) — keeps the relay's view of the private wiki/document repos current, handles the two-writer race with a desktop Claude Code session.

## Why the relay can't reuse existing skills or routines

- **Skills** (`remember`, `recall`, `sync-calendar`, etc.) only run inside a Claude Code session — there's no mechanism to invoke one from an external process.
- **`claude.ai/code` routines** were considered and rejected for this: routines cannot attach private GitHub repos (confirmed bug, github.com/anthropics/claude-code/issues/64130), and `backend/memory-module/wiki/` is gitignored from the public `Butler` repo specifically so it's never exposed there — a routine cloning the public repo would see the skill definitions but no actual memory data.
- Instead, the relay makes its own direct Anthropic API calls with its own tool-use loop, operating on the *same file conventions* documented in `docs/db/memory-module.md` — a second implementation against a shared convention, the same relationship `sync-calendar` already has to `remember`. This means the wiki file format itself never changes for this epic.

## Data flow

```
Phone (Telegram) --voice note--> Telegram Bot API --webhook--> Voice Relay (FastAPI)
                                                                     |
                                                verify secret_token + chat_id allowlist
                                                                     |
                                                download .ogg --> STT (OpenAI)
                                                                     |
                                                Anthropic Messages API, tool-use loop:
                                                  - list_wiki_pages / read_wiki_page (+ [[wiki-link]] following)
                                                  - append_reminder / save_memory
                                                  - create_calendar_event (direct Google Calendar API)
                                                  - find_document (metadata-only)
                                                + per-chat_id short-term session history (SQLite, TTL)
                                                                     |
                                                reply text --> TTS (OpenAI) --> voice note --> Telegram --> phone
```

## Technology decisions

- **Python + FastAPI/uvicorn** — matches this repo's existing Python usage (the wiki/document validator scripts), containerizes cleanly for the Phase 2 VPS move.
- **STT + TTS: OpenAI** — one extra provider account instead of two. Telegram voice notes are complete OGG/Opus clips (not a live stream), so a single batch STT call is the right fit; no streaming STT needed.
- **Anthropic API directly** (not via Claude Code) — `ANTHROPIC_API_KEY`, default model `claude-sonnet-5` (cost/latency-appropriate for short conversational tool-use turns), swappable via `CLAUDE_MODEL` env var.
- **Telegram**: raw `httpx` calls to the Bot API — the surface is narrow (one webhook, `getFile`, `sendVoice`/`sendAudio`), not worth a full dispatcher framework.
- **Google Calendar**: direct `google-api-python-client` calls with a dedicated OAuth "Desktop app" client — separate from and independent of Claude Code's Calendar connector, since this is a different OS process with no access to that connector.

## Non-functional constraints

- **Billing**: this relay incurs its own Anthropic/OpenAI/Google API costs, separate from the Claude Code/claude.ai subscription — documented prominently (`README.md`) so it's not a surprise.
- **Privacy**: same rule as the rest of the repo — no real personal data in anything committed to the public repo. Secrets live only in `backend/voice-relay/.env` (gitignored).
- **Concurrency**: the relay and a desktop Claude Code session can both write to the same wiki files. Mitigated with `git pull --rebase` before reads/writes and a retry-once-then-log (not fail) policy on push conflicts — the same "local save stands, backup push failure reported not fatal" philosophy `remember` already established, applied to a two-writer scenario instead of one.
- **Latency**: STT + each tool-call round trip + TTS + Telegram upload/download all stack. Bounded (not eliminated) by capping wiki-link-following hops per turn (~4).
- **Single-user security boundary**: no JWT/OAuth for end users (deliberately, single-user) — the boundary is the webhook's random path, Telegram's `secret_token` header, and a hard `chat_id` allowlist. Anything else is dropped, never processed.

## Downstream stage applicability

- **API Design: Applicable** (unlike Memory/Document modules) — this epic genuinely exposes a network API (the Telegram webhook, a health endpoint). See `docs/api/voice-relay.md`.
- **Database Design: Applicable, but minimal** — only the short-term session store needs real schema (SQLite); the wiki/document data reuses existing file conventions unchanged. See `docs/db/voice-relay.md`.
- **UI: Not applicable** — Telegram itself is the interface; no dedicated UI is built. See `docs/ui/voice-relay.md`.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `domain-designer` — a real (if small) domain model exists here: a `Session` entity, distinct from `WikiPage`.

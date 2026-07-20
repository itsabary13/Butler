# Architecture: Voice Relay

## Why this breaks the "no server" rule

Every other Butler capability (Memory, Documents) runs entirely inside a Claude Code session — no server, no database, no API. This epic is the deliberate, single exception: genuine voice (speak from anywhere, hear a reply) requires real speech-to-text/text-to-speech integration, and there's no way to wire that up without a server-side piece. Confirmed before designing this: Claude Code's own `/voice` dictation is terminal-only and doesn't work over Remote Control; there's no text-to-speech anywhere in Claude's consumer products.

## Module boundaries

1. **Telegram interface** (`app/telegram.py`) — receives voice messages via webhook, sends voice replies.
2. **Speech layer** (`app/stt.py`, `app/tts.py`) — local, offline transcription and synthesis (see v1.1 addendum below).
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
                                                download .ogg --> STT (faster-whisper, local)
                                                                     |
                                                Anthropic Messages API, tool-use loop:
                                                  - list_wiki_pages / read_wiki_page (+ [[wiki-link]] following)
                                                  - append_reminder / save_memory
                                                  - create_calendar_event (direct Google Calendar API)
                                                  - find_document (metadata-only)
                                                + per-chat_id short-term session history (SQLite, TTL)
                                                                     |
                                                reply text --> TTS (Piper, local) --> voice note --> Telegram --> phone
```

## Technology decisions

- **Python + FastAPI/uvicorn** — matches this repo's existing Python usage (the wiki/document validator scripts), containerizes cleanly for the Phase 2 VPS move.
- **STT + TTS: local models (faster-whisper + Piper)** — see the v1.1 addendum below; originally OpenAI, replaced before Task 43's live verification.
- **Anthropic API directly** (not via Claude Code) — `ANTHROPIC_API_KEY`, default model `claude-sonnet-5` (cost/latency-appropriate for short conversational tool-use turns), swappable via `CLAUDE_MODEL` env var.
- **Telegram**: raw `httpx` calls to the Bot API — the surface is narrow (one webhook, `getFile`, `sendVoice`/`sendAudio`), not worth a full dispatcher framework.
- **Google Calendar**: direct `google-api-python-client` calls with a dedicated OAuth "Desktop app" client — separate from and independent of Claude Code's Calendar connector, since this is a different OS process with no access to that connector.

## Non-functional constraints

- **Billing**: this relay incurs its own Anthropic and Google Calendar API costs, separate from the Claude Code/claude.ai subscription — documented prominently (`README.md`) so it's not a surprise. Speech-to-text/text-to-speech are local (v1.1 addendum below) and carry no per-request billing.
- **Privacy**: same rule as the rest of the repo — no real personal data in anything committed to the public repo. Secrets live only in `backend/voice-relay/.env` (gitignored).
- **Concurrency**: the relay and a desktop Claude Code session can both write to the same wiki files. Mitigated with `git pull --rebase` before reads/writes and a retry-once-then-log (not fail) policy on push conflicts — the same "local save stands, backup push failure reported not fatal" philosophy `remember` already established, applied to a two-writer scenario instead of one.
- **Latency**: STT + each tool-call round trip + TTS + Telegram upload/download all stack. Bounded (not eliminated) by capping wiki-link-following hops per turn (~4).
- **Single-user security boundary**: no JWT/OAuth for end users (deliberately, single-user) — the boundary is the webhook's random path, Telegram's `secret_token` header, and a hard `chat_id` allowlist. Anything else is dropped, never processed.

## Downstream stage applicability

- **API Design: Applicable** (unlike Memory/Document modules) — this epic genuinely exposes a network API (the Telegram webhook, a health endpoint). See `docs/api/voice-relay.md`.
- **Database Design: Applicable, but minimal** — only the short-term session store needs real schema (SQLite); the wiki/document data reuses existing file conventions unchanged. See `docs/db/voice-relay.md`.
- **UI: Not applicable** — Telegram itself is the interface; no dedicated UI is built. See `docs/ui/voice-relay.md`.

## v1.1 addendum — local STT/TTS (no OpenAI dependency)

While setting up real credentials for Task 43 (live verification), the user declined to create an OpenAI account — Anthropic billing is accepted as unavoidable (Claude is the whole point of Butler), but a second pay-per-usage provider for speech was an avoidable cost, not a necessary one. Replaced before any real OpenAI account was ever created:

- **STT**: `faster-whisper` (a CTranslate2 reimplementation of OpenAI's own open-weight Whisper model) — runs fully offline after a one-time model download (free, cached locally, no account). Model size configurable via `WHISPER_MODEL_SIZE` (default `small`).
- **TTS**: `piper` — fully offline neural TTS, MIT-licensed, no account. Needs a one-time voice model download (`scripts/download_piper_voice.py`, mirroring the existing `google_oauth_setup.py` one-time-script pattern) rather than a runtime dependency. Output is WAV, converted to Opus/OGG via `ffmpeg` (already a dependency for Telegram voice notes) exactly as the OpenAI path did.
- Both were chosen over other free/local options (`edge-tts`, `pyttsx3`) specifically because they're genuinely offline once set up — no dependency on any third-party service at request time, not just "no billing."
- **Trade-off accepted**: latency shifts from network-bound (an OpenAI API round trip) to CPU-bound (local inference) — slower per-request on modest hardware, and the first call after a cold start is slower still (model load). Acceptable for a single-user relay; revisit if real usage shows this is a problem.
- Verified locally end-to-end (piper → ffmpeg → Opus bytes → faster-whisper transcription) with zero `OPENAI_API_KEY` anywhere — see `docs/tests/voice-relay.md`.
- No change to `app/main.py`/`app/anthropic_client.py`/`app/telegram.py` — `stt.transcribe()`/`tts.synthesize()` keep the same interface, so this was a pure implementation swap behind an unchanged boundary.

## v1.2 addendum — Phase 2: VPS deployment

Originally deferred ("Phase 2, a separate, future epic", `specs/epics/voice-relay.md`), moved up when a corporate laptop's network turned out to block `api.telegram.org` outright (a proxy policy denying the "Chat/Instant Messaging" category) — blocking Phase 1's own local verification, not just incidental to it. A VPS has its own unrestricted connection, so it resolves this permanently rather than working around it network-by-network.

- **Host**: DigitalOcean droplet (1 GB/1 vCPU + a 1GB swap file, `fra1`), Ubuntu 24.04 — swap absorbs faster-whisper's transcription-time memory spike, avoiding the cost of a 2GB droplet for RAM that would mostly sit idle. Resizable later if real usage shows it's too tight.
- **Deployment**: Docker Compose, two services — the existing `Dockerfile`'s image (`voice-relay`) and `caddy:2` as a reverse proxy providing automatic Let's Encrypt TLS for the Telegram webhook's required HTTPS endpoint.
- **Persistence**: session store (`data/`), the wiki/document private-repo clones, and the faster-whisper model cache all live outside the container as volumes/bind mounts, so a redeploy (`docker compose up -d --build`) doesn't lose them.
- **No `app/` code changes** — `wiki_dir()`/`docs_dir()`/`DB_PATH` already resolve correctly given the right `.env` values (absolute container paths instead of local-dev-relative ones); this was purely a hosting/ops change with a new `.env` shape, not a design change. See `backend/voice-relay/DEPLOY.md` for the concrete runbook.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `domain-designer` — a real (if small) domain model exists here: a `Session` entity, distinct from `WikiPage`.

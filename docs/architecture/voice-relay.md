# Architecture: Voice Relay

## Why this breaks the "no server" rule

Every other Butler capability (Memory, Documents) runs entirely inside a Claude Code session — no server, no database, no API. This epic is the deliberate, single exception: genuine voice (speak from anywhere, hear a reply) requires real speech-to-text/text-to-speech integration, and there's no way to wire that up without a server-side piece. Confirmed before designing this: Claude Code's own `/voice` dictation is terminal-only and doesn't work over Remote Control; there's no text-to-speech anywhere in Claude's consumer products.

## Module boundaries

1. **Telegram interface** (`app/telegram.py`) — receives voice, text, and document messages via webhook (see v3 addendum below); sends voice or text replies.
2. **Speech layer** (`app/stt.py`, `app/tts.py`) — local, offline transcription and synthesis (see v1.1 addendum below).
3. **Reasoning layer** (`app/claude_code_client.py`) — headless Claude Code (`claude -p`, subscription-billed — see v2 addendum below); this is the relay's "brain," standing in for what a Claude Code session + skills would normally do.
4. **Tools** (`app/tools/`) — `wiki_tools.py`, `calendar_tools.py`, `document_tools.py`, `session_store.py` — the relay's own implementations of memory/calendar/document access, since it cannot invoke Claude Code skills directly.
5. **Wiki/document sync** (`app/wiki_sync.py`) — keeps the relay's view of the private wiki/document repos current, handles the two-writer race with a desktop Claude Code session.

## Why the relay can't reuse existing skills or routines

- **Skills** (`remember`, `recall`, `sync-calendar`, etc.) only run inside a Claude Code session — there's no mechanism to invoke one from an external process.
- **`claude.ai/code` routines** were considered and rejected for this: routines cannot attach private GitHub repos (confirmed bug, github.com/anthropics/claude-code/issues/64130), and `backend/memory-module/wiki/` is gitignored from the public `Butler` repo specifically so it's never exposed there — a routine cloning the public repo would see the skill definitions but no actual memory data.
- Instead, the relay invokes headless Claude Code itself (see v2 addendum below) against tools operating on the *same file conventions* documented in `docs/db/memory-module.md` — a second implementation against a shared convention, the same relationship `sync-calendar` already has to `remember`. This means the wiki file format itself never changes for this epic.

## Data flow

```
Phone (Telegram) --voice note--> Telegram Bot API --webhook--> Voice Relay (FastAPI)
                                                                     |
                                                verify secret_token + chat_id allowlist
                                                                     |
                                                download .ogg --> STT (faster-whisper, local)
                                                                     |
                                                headless `claude -p` (subscription-billed), MCP tools:
                                                  - read_wiki_page (+ [[wiki-link]] following)
                                                  - append_reminder / save_memory
                                                  - create_calendar_event (direct Google Calendar API)
                                                  - find_document (metadata-only)
                                                + per-chat_id --resume session_id (SQLite, TTL)
                                                                     |
                                                reply text --> TTS (Piper, local) --> voice note --> Telegram --> phone
```

## Technology decisions

- **Python + FastAPI/uvicorn** — matches this repo's existing Python usage (the wiki/document validator scripts), containerizes cleanly for the Phase 2 VPS move.
- **STT + TTS: local models (faster-whisper + Piper)** — see the v1.1 addendum below; originally OpenAI, replaced before Task 43's live verification. STT restricts language detection to `en`/`he`/`ru` (`app/stt.py`'s `ALLOWED_LANGUAGES`) rather than Whisper's unrestricted ~99-language guess, after live testing misdetected a real Hebrew message.
- **Headless Claude Code, not a direct Anthropic API key** — see the v2 addendum below; `CLAUDE_CODE_OAUTH_TOKEN` for subscription auth, model swappable via `CLAUDE_CODE_MODEL` env var (blank = CLI default).
- **Telegram**: raw `httpx` calls to the Bot API — the surface is narrow (one webhook, `getFile`, `sendVoice`/`sendAudio`), not worth a full dispatcher framework.
- **Google Calendar**: direct `google-api-python-client` calls with a dedicated OAuth "Desktop app" client — separate from and independent of Claude Code's Calendar connector, since this is a different OS process with no access to that connector.

## Non-functional constraints

- **Billing**: answering rides the existing Claude Pro/Max subscription's usage allowance (v2 addendum below), not a separate pay-per-token API cost — the only other ongoing costs are Google Calendar API usage (free tier) and VPS/domain hosting (`DEPLOY.md`). Speech-to-text/text-to-speech are local (v1.1 addendum below) and carry no per-request billing. Documented prominently (`README.md`) so it's not a surprise.
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

## v2 addendum — headless Claude Code instead of direct Anthropic API billing

The user changed the billing constraint after Phase 2 was already live: no pay-as-you-go API usage at all, only the existing Claude Pro subscription (VPS/domain cost accepted, per-token API cost not). `app/anthropic_client.py`'s direct `anthropic.Anthropic().messages.create()` tool-use loop is exactly the pay-per-token surface that violates that, so it's replaced rather than kept.

- **New answering mechanism**: `app/claude_code_client.py` shells out to the `claude` CLI in headless/non-interactive mode (`claude -p ... --output-format json`), authenticated via `CLAUDE_CODE_OAUTH_TOKEN` (generated once locally with `claude setup-token`, pasted into `.env` — same "generate locally, paste into VPS `.env`" pattern already used for `GOOGLE_OAUTH_REFRESH_TOKEN`). This draws on the Pro/Max subscription's usage allowance, the same quota `claude.ai`/interactive Claude Code draws from, instead of separate per-token billing.
- **Tools move to MCP**: the five tools (`read_wiki_page`, `save_memory`, `append_reminder`, `create_calendar_event`, `find_document`) are now exposed via a local stdio MCP server (`app/mcp_server.py`, registered in `mcp-config.json`) instead of hand-rolled Anthropic tool-use JSON schemas. The underlying `app/tools/*` implementations — including the reviewed slug path-traversal guard and create-only calendar constraint — are unchanged; only the transport changed. `--allowedTools` is passed as an explicit allowlist of just those 5 MCP tools, so the headless process has no Bash or filesystem access beyond them (least-privilege, same spirit as the webhook's own hard `chat_id` allowlist).
- **Session history simplifies**: multi-turn context now uses Claude Code's own `--resume <session_id>` instead of manually replaying a capped transcript. `app/tools/session_store.py` stores just the returned `session_id` per `chat_id` (still TTL-bounded, still SQLite) — `docs/db/voice-relay.md`'s `Session.history` field is superseded by `Session.claude_session_id`. The old manual `MAX_TOOL_ROUNDS`/`MAX_WIKI_LINK_HOPS` bookkeeping is gone too — that budgeting is now Claude Code's own concern, not this app's. A stored `session_id` can go stale independently of our own TTL (a VPS redeploy wipes Claude Code's own session storage) — `get_reply` retries once with a fresh session if `--resume` fails, rather than failing the turn.
- **VPS image change**: the Dockerfile now installs Node.js + `@anthropic-ai/claude-code` alongside the existing `ffmpeg`/`git`, since the `claude` binary itself is the new runtime dependency.
- **Trade-off accepted**: Pro/Max usage is rate-limited (weekly caps), not unmetered — acceptable for a single-user assistant, but a real constraint the old pay-per-token design didn't have. Revisit if real usage runs into the cap.
- **Not reopened**: the v1.1 (local STT/TTS) and v1.2 (VPS hosting) addenda are unaffected — `stt.transcribe()`/`tts.synthesize()` and the Docker Compose/Caddy hosting shape are untouched by this swap.

## v3 addendum — text and document input (specs/epics/voice-relay.md's v1.4)

The webhook handler (`app/main.py`) now branches on message type instead of only ever looking for `voice`:

- **Text**: `telegram.extract_text_message` → `_handle_text_message` calls the exact same `claude_code_client.get_reply(chat_id, text)` voice already uses (same MCP tools, same `--resume` session continuity, same wiki/document sync before and after) — the only difference from voice is skipping `stt.transcribe`/`tts.synthesize` and replying via `send_text_reply` instead of `send_voice_reply`. This means a text conversation and a voice conversation in the same chat share session continuity — Claude Code's own `--resume` doesn't care which input modality produced a given turn.
- **Document**: `telegram.extract_document_message` → `_handle_document_message` downloads the file and calls `app/tools/document_tools.py`'s new `save_document(filename, content_bytes, title=caption)` directly — **not** through `claude`. File bytes can't reasonably flow through an MCP tool-call's JSON arguments, and the save itself is a deterministic operation (derive a slug, write two files) with nothing for an LLM to reason about, so this deliberately bypasses the `claude` subprocess entirely rather than inventing a way to smuggle binary data through it. Confirmation is a plain `Saved "<title>".` reply, not LLM-phrased.
- **Photo** (added after live testing showed images sent via Telegram's ordinary Photo picker were silently dropped — that flow sends a distinct `message.photo` field, not `message.document`, which only covers the separate "File" attachment path): `telegram.extract_photo_message` picks the highest-resolution `PhotoSize` (Telegram lists them smallest to largest) and routes straight into the *same* `_process_document_message`/`save_document` path as a document upload, with a synthesized `photo.jpg` filename since Telegram photos never carry an original one. No new handler — reuses the document pipeline entirely.
- **`save_document`** reuses `docs/db/document-module.md`'s exact sidecar format (same required frontmatter fields, same slug-disambiguation-on-collision philosophy as Memory) — a document saved this way is indistinguishable from one saved by the `add-document` skill, and immediately shows up to `find_document` (already an MCP tool voice/text conversations can call).
- **Auth model unchanged**: the secret check still runs first, unconditionally, before any payload-shape branching (the same ordering fixed in the original review). The `chat_id` ownership check now runs once, generically, after determining *some* actionable message type was found (voice, document, photo, or text) — a message type none of the four extractors recognize (sticker, edited_message, etc.) is still silently accepted without a `chat_id` check, same as before, since there's nothing to authorize when nothing is going to be processed either way.
- **New finding, fixed in the same pass**: `save_document`'s file extension comes straight from the sender's own Telegram filename — unlike `slug` (always passed through `slugify()`), the extension was only `.lower()`'d, not validated, so a crafted filename could smuggle a `/` or `..` into the saved path. Fixed with `VALID_EXT = re.compile(r"^[a-z0-9]{1,10}$")`, falling back to `bin` on anything that doesn't match. See `docs/reviews/voice-relay.md`'s v3 addendum.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `domain-designer` — a real (if small) domain model exists here: a `Session` entity, distinct from `WikiPage`.

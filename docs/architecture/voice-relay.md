# Architecture: Voice Relay

## Why this breaks the "no server" rule

Every other Butler capability (Memory, Documents) runs entirely inside a Claude Code session — no server, no database, no API. This epic is the deliberate, single exception: genuine voice (speak from anywhere, hear a reply) requires real speech-to-text/text-to-speech integration, and there's no way to wire that up without a server-side piece. Confirmed before designing this: Claude Code's own `/voice` dictation is terminal-only and doesn't work over Remote Control; there's no text-to-speech anywhere in Claude's consumer products.

## Module boundaries

1. **Telegram interface** (`app/telegram.py`) — receives voice, text, and document messages via webhook (see v3 addendum below); sends voice or text replies.
2. **Speech layer** (`app/stt.py`, `app/tts.py`) — local, offline transcription and synthesis (see v1.1 addendum below).
3. **Reasoning layer** (`app/claude_code_client.py`) — headless Claude Code (`claude -p`, subscription-billed — see v2 addendum below); this is the relay's "brain," standing in for what a Claude Code session + skills would normally do.
4. **Tools** (`app/tools/`) — `wiki_tools.py`, `calendar_tools.py`, `document_tools.py`, `session_store.py`, `notification_store.py` (v5 addendum) — the relay's own implementations of memory/calendar/document/notification access, since it cannot invoke Claude Code skills directly.
5. **Wiki/document sync** (`app/wiki_sync.py`) — keeps the relay's view of the private wiki/document repos current, handles the two-writer race with a desktop Claude Code session.
6. **Proactive scan** (`app/proactive.py`, v5 addendum) — the one path that initiates contact rather than reacting to an inbound message; scheduled via `AsyncIOScheduler` inside `app/main.py`'s `lifespan`.

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
- **Outbound-initiated messaging** (v5 addendum): every path above only ever acts in response to the user's own message. The proactive scan is the one exception — see that addendum for why the model can only propose a notification, never send one directly.

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

### Found live, fixed — no Piper voice exists for Hebrew

A real Hebrew voice message got back a long, garbled, nonsensical voice reply. Root cause: Claude naturally replies in the same language it's addressed in (nothing forces English), and Piper — unlike a cloud TTS API — has a fixed per-language voice catalog with no Hebrew voice in it at all (confirmed against `rhasspy/piper`'s own voice list; Russian has voices, Hebrew doesn't). Feeding the loaded English voice Hebrew text doesn't fail — it mispronounces every word against English phoneme rules, producing exactly that kind of garbled audio instead of a clean error.

`stt.transcribe()` now returns `(text, language)` instead of just `text` — the detected language was already being computed internally (`ALLOWED_LANGUAGES` restriction, above) but discarded before this fix. `tts.UNSUPPORTED_LANGUAGES` (currently just `{"he"}`) documents which of `ALLOWED_LANGUAGES` Piper genuinely cannot speak. `app/main.py`'s `_handle_voice_message` checks the detected language against it and sends a normal text reply instead of attempting synthesis when it matches — reusing the same `send_text_reply` path the text-message handler already uses, rather than adding a new reply mechanism. No cloud TTS fallback added (would reopen the per-request-billing/account trade-off this addendum specifically avoided); revisit only if a real offline Hebrew voice becomes available.

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
- **Document**: `telegram.extract_document_message` → `_handle_document_message` downloads the file and calls `app/tools/document_tools.py`'s new `save_document(filename, content_bytes, title=caption)` directly — **not** through `claude`. File bytes can't reasonably flow through an MCP tool-call's JSON arguments, and the save itself is a deterministic operation (derive a slug, write two files) with nothing for an LLM to reason about, so this deliberately bypasses the `claude` subprocess entirely rather than inventing a way to smuggle binary data through it. This is now a placeholder save, superseded moments later by the v4 addendum's content-read pass below — the confirmation reply comes from that second step, not this one.
- **Photo** (added after live testing showed images sent via Telegram's ordinary Photo picker were silently dropped — that flow sends a distinct `message.photo` field, not `message.document`, which only covers the separate "File" attachment path): `telegram.extract_photo_message` picks the highest-resolution `PhotoSize` (Telegram lists them smallest to largest) and routes straight into the *same* `_process_document_message`/`save_document` path as a document upload, with a synthesized `photo.jpg` filename since Telegram photos never carry an original one. No new handler — reuses the document pipeline entirely.
- **`save_document`** reuses `docs/db/document-module.md`'s exact sidecar format (same required frontmatter fields, same slug-disambiguation-on-collision philosophy as Memory) — a document saved this way is indistinguishable from one saved by the `add-document` skill, and immediately shows up to `find_document` (already an MCP tool voice/text conversations can call).
- **Auth model unchanged**: the secret check still runs first, unconditionally, before any payload-shape branching (the same ordering fixed in the original review). The `chat_id` ownership check now runs once, generically, after determining *some* actionable message type was found (voice, document, photo, or text) — a message type none of the four extractors recognize (sticker, edited_message, etc.) is still silently accepted without a `chat_id` check, same as before, since there's nothing to authorize when nothing is going to be processed either way.
- **New finding, fixed in the same pass**: `save_document`'s file extension comes straight from the sender's own Telegram filename — unlike `slug` (always passed through `slugify()`), the extension was only `.lower()`'d, not validated, so a crafted filename could smuggle a `/` or `..` into the saved path. Fixed with `VALID_EXT = re.compile(r"^[a-z0-9]{1,10}$")`, falling back to `bin` on anything that doesn't match. See `docs/reviews/voice-relay.md`'s v3 addendum.

## v4 addendum — documents are actually read (`specs/epics/voice-relay.md`'s v1.5)

v1.4's `save_document` never looked at a file's *content*, only its filename/caption — `find_document` could match "passport scan" only if that exact phrase was already the title. Live testing surfaced this directly (an uncaptioned theater-ticket photo was completely unfindable). Fixed with a second pass after the placeholder save:

- **`app/claude_code_client.py`'s `enrich_document(file_path, slug, initial_title, caption)`** — a standalone `claude -p` invocation (no `--resume`; this isn't a chat turn, the wiki itself is what carries the content forward, not session state) that reads the saved file and calls two tools: the new `categorize_document` (renames to a content-derived title, adds a short category) and the existing `save_memory` (if there's something genuinely worth remembering — key facts, dates, visible text — so it's answerable later via normal recall, not just findable by title).
- **First filesystem `Read` access anywhere in this relay.** Every prior design decision (the original review, the v2 headless-Claude-Code swap) deliberately kept the conversational path (voice/text) to *zero* filesystem access — only the 5 MCP tools, explicitly reviewed as a stricter boundary than even the old direct-API design. `enrich_document` breaks that pattern out of necessity (there's no way to let `claude` *see* an uploaded image without some form of file read), so the blast radius is minimized instead: `Read` is granted only for this one standalone call, scoped via `--add-dir` to just `file_path.parent` (the docs directory) — not the app source, not the wiki, not `.env`. (`.env` in particular is never a file on disk inside the container at all — `docker-compose.yml`'s `env_file` only injects it as process environment variables — so even an unscoped `Read` couldn't reach it; the `--add-dir` scoping is still the right hardening regardless, since the goal is "can't read anything it doesn't need," not "happens not to contain a secret today.") `--allowedTools` for this pass is `Read,mcp__butler__categorize_document,mcp__butler__save_memory` — narrower than the conversational `ALLOWED_TOOLS`, since this pass has no reason to touch calendar/reminders/find_document.
- **`categorize_document`** (`app/tools/document_tools.py`) is safe to expose as an MCP tool where `save_document` isn't, because it operates on an *already-saved* file by slug reference — no raw bytes need to cross the tool-call boundary. It renames `<slug>.<ext>`/`<slug>.md` to a new slug (same disambiguate-on-collision rule as a fresh save) and adds an optional `category` frontmatter field.
- **Residual risk, accepted**: an uploaded document's content reaches the model as untrusted input (the same is already true of a voice transcript or a typed message), so a crafted document could attempt to steer `save_memory`/`categorize_document` calls via embedded instructions (indirect prompt injection). Bounded by the same tight `--allowedTools` scoping — worst case is a spurious/misleading memory or mislabeled document, not filesystem or credential exposure, since `Read` still can't reach anything outside the docs directory.

## v5 addendum — proactive notifications (`specs/epics/voice-relay.md`'s v1.6)

Every capability so far only ever acts in response to the user's own message. This adds the first exception: a daily unattended scan that can message the user unprompted when it finds a genuine action item.

- **The model proposes, Python decides and sends.** `app/claude_code_client.py`'s `run_proactive_check()` is a standalone `claude -p` invocation — same shape as `enrich_document` (own prompt, own narrow `--allowedTools`, no `--resume`; this scan has no notion of an ongoing conversation). It reads the wiki manifest/`reminders` page and calls the new `list_upcoming_events` tool, then may call the new `propose_notification` tool for anything genuinely worth an unprompted interruption. `propose_notification` (`app/tools/notification_store.py`) only records a candidate — it has no mechanism to send anything itself. `app/proactive.py`'s `run_daily_scan()` then reads whatever was proposed during that run and is the *only* thing that ever calls `telegram.send_text_reply` unprompted, after applying: cooldown-based dedup (`was_recently_sent`, skip a `dedup_key` sent within `PROACTIVE_COOLDOWN_DAYS`), a hard daily cap (`PROACTIVE_MAX_PER_DAY`, checked via `sent_count_last_24h`), and quiet hours (`QUIET_HOURS_START`/`_END`, in `LOCAL_TIMEZONE`) — a proposal outside any of these is marked `deferred`/`suppressed`, never sent, but can legitimately be re-proposed on a later run if still true.

  This is a deliberate departure from the `save_memory`/`categorize_document` pattern the model can already call directly elsewhere in this relay: those are reversible, user-invisible internal writes; an outbound Telegram ping is user-visible, irreversible, and initiated with no human in the loop at all (every other tool call happens because the user just sent a message — this one doesn't). The chokepoint means a misbehaving or prompt-injected scan can at worst fill a proposals table Python then caps; it can never itself spam the user.

- **One detection path, not two.** The user's two example cases — "an appointment" (looks deterministic: diff against the Calendar) and "time for a checkup" (inherently fuzzy: a pattern noticed in wiki content) — are handled by the *same* invocation rather than a hand-rolled deterministic Python path for the first. `reminders.md`'s rule field is freeform text with no fixed grammar (`- every 10th: pay storage invoice`), so a meaningful share of "appointment-like" items already require LLM interpretation; splitting the two would also mean two separate places for dedup logic to diverge. Determinism is preserved where it actually matters — never double-notify, never spam — by putting it in the Python gate, not in detection.

- **New tools**: `calendar_tools.py`'s `list_upcoming_events(days_ahead=7)` (read-only — `create_calendar_event`'s existing `calendar.events` OAuth scope already covers `events().list()`, no new consent needed) and `notification_store.py`'s `propose_notification`/dedup functions, both wrapped in `app/mcp_server.py`. `PROACTIVE_ALLOWED_TOOLS` (`claude_code_client.py`) deliberately excludes `save_memory`, `append_reminder`, and `create_calendar_event` — an unattended scan reads and proposes, it never mutates the wiki or calendar.

- **Scheduling**: `AsyncIOScheduler` (APScheduler) started in `app/main.py`'s new `lifespan` context manager, inside the same single `uvicorn` process — no new container (`docker-compose.yml` stays `voice-relay` + `caddy`), and critically no new network-reachable endpoint, since the trigger's only purpose is "cause an unprompted message" and that surface shouldn't be externally triggerable. The blocking `claude` subprocess call runs via `asyncio.to_thread`, same reasoning as the webhook path's `BackgroundTasks`. **Hard constraint**: the Dockerfile's `CMD` must stay a single worker (no `uvicorn --workers`) — more than one would double-fire the daily job (mitigated regardless with `max_instances=1, coalesce=True`).

- **Fix from live verification: dedup keys need a memory, or dedup silently does nothing.** `run_proactive_check` has no `--resume` — each run is a fresh invocation with zero memory of the previous one. For a Calendar-backed item that's harmless (the event's own `id` is naturally the same every day), but a fuzzy wiki-derived item (the "checkup due" case) has no natural stable id, so the model was inventing a plausible-sounding `dedup_key` from scratch each run — a *different* one each time, which silently defeated `was_recently_sent`'s cooldown check entirely (confirmed live: running the scan twice in a row sent the same notification twice). Fixed by giving the prompt actual memory: `notification_store.get_recent(days=PROACTIVE_COOLDOWN_DAYS)` is embedded directly in `run_proactive_check`'s prompt text (not a tool call — same "just tell it" approach as the wiki manifest already baked into `_system_prompt()`), listing every recent notification's `dedup_key`/`message`/`status`, with an explicit instruction to reuse a listed key when re-flagging the same thing. The Python-side gate (`was_recently_sent`) was already correct — the bug was entirely upstream of it, in the model never being given the information it needed to produce a stable key in the first place.

- **Why not a Claude Code Routine**: `backend/memory-module` already tried exactly this and hit two confirmed platform walls (`specs/epics/memory-module.md`'s v1.4 section) — Routines can't attach private GitHub repos, and have no secret/env-var storage, so a Routine can use neither this repo's private wiki nor a Telegram bot token. This relay has neither constraint (real server, real `.env`, wiki already on the same VPS), which is the whole reason to build this here instead of revisiting Routines.

- **Off by default**: `PROACTIVE_ENABLED=false` — deploying this code changes nothing until explicitly turned on, after a manual live-verification pass (`DEPLOY.md`).

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

This epic's full lifecycle (domain/API/DB/UI/implementation/tests/review/docs) is complete through v1.6 — no further stage hand-off pending. Future increments follow the same addendum pattern as v1.1–v1.6 above.

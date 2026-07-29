# Epic: Voice Relay

**Status: Shipped** — live on the Phase 2 VPS (`jarvis.irenets.online`), Task 43's end-to-end verification against real credentials complete: voice and text conversation, memory save/recall, document upload, and Google Calendar event creation all confirmed working through the real deployment. See the v1.1–v1.5 addenda below for what changed since the original v1 design (local STT/TTS, VPS hosting, subscription billing instead of pay-per-token, text/document input). v1.6 (proactive notifications)'s own manual live-verification pass (`DEPLOY.md`) is also complete: the daily scan ran live against real Calendar/wiki data, correctly identified an actionable reminder, and — after the dedup-drift fix below — correctly withheld a second, duplicate send for the same already-sent item on a subsequent run. `PROACTIVE_ENABLED` remains an opt-in setting (`false` by default) but the feature itself is confirmed working end-to-end. v1.7 (Calendar viewing + Gmail access) is now live-verified too: `GOOGLE_OAUTH_REFRESH_TOKEN` was rotated to the combined `calendar.events` + `gmail.modify` scope, and both a real Calendar event creation and a real `list_recent_emails` call against the live Gmail account were confirmed working on the deployed VPS. v1.8 (Calendar update/delete, web search, subscription tracking) is deployed; subscription tracking (record + proactive nudge) is live-verified on the VPS, Calendar update/delete and web search verification is in progress. A timezone bug was found live during this rollout — proactive alerts and calendar event creation were using the wrong timezone, since the model and the Calendar API integration never actually knew the user's configured local timezone — fixed (see the architecture doc's own addendum on this).

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

## v1.4 addendum — text and document input, not just voice

Extended beyond "voice is the only supported input" (original IN SCOPE list above): the same Telegram webhook now also accepts plain text messages and document (file) uploads.

- **Text messages** answer through the exact same "brain" as voice (`app/claude_code_client.py`, same tools, same `--resume` session continuity) — just skip STT and reply with text instead of a voice note. No new capability, just a second way to reach the same five tools.
- **Document uploads** are saved as a new `Document` using the *exact* existing `docs/db/document-module.md` sidecar convention `find_document` already reads — a file saved this way is immediately findable by voice or text ("find my passport scan"). This does **not** go through `claude` — file bytes can't reasonably flow through an MCP tool-call's JSON arguments, so `app/tools/document_tools.py`'s `save_document` is called directly and deterministically from `app/main.py`, using the Telegram caption (if any) as the title. Covers both of Telegram's two distinct upload shapes: a "File" attachment (`message.document`, original filename preserved) and the ordinary Photo picker/camera button (`message.photo`, compressed, no filename — Telegram sends multiple resolutions per photo, the highest-resolution one is used, with a synthesized `photo.jpg` filename).
- No scope change to the Calendar/Reminder/Memory tools themselves, and voice remains fully supported unchanged — this only widens which message *types* the webhook accepts.
- See `docs/architecture/voice-relay.md`'s v3 addendum for the full design and `docs/reviews/voice-relay.md` for a path-traversal finding (and fix) in the new document-saving code.

## v1.5 addendum — documents are read, named, categorized, and made askable

v1.4's document save was metadata-only: `find_document` could only ever match a document's *title* (the Telegram caption, or a generic fallback like `"photo"` if none was given) — never its actual content. Live testing surfaced this directly: an uncaptioned photo of theater tickets was unfindable by anything describing what was actually in it. Extended so uploads are genuinely read, not just filed:

- **Auto-naming and categorization**: after the initial placeholder save, a second, separate `claude` invocation (`app/claude_code_client.py`'s `enrich_document`) reads the file's actual content and calls a new `categorize_document` tool to rename it to a content-derived title and tag it with a short category ("ticket," "receipt," "ID," etc.) — no caption required.
- **Made askable, not just findable**: the same pass saves anything genuinely worth remembering about the content into the wiki via the existing `save_memory` tool, so "what does my Habima ticket say" is answerable through normal recall, not just a title-substring match.
- **New filesystem access, tightly scoped**: this is the first time the headless process gets any `Read` access at all — the conversational path (voice/text) deliberately still has none. Scoped via `--add-dir` to just the docs directory, with a narrower `--allowedTools` than conversation (`Read` + `categorize_document` + `save_memory` only — no calendar/reminders/find_document) and no `--resume` (not a chat turn). See `docs/architecture/voice-relay.md`'s v4 addendum and `docs/reviews/voice-relay.md` for the full security reasoning.
- **Schema note**: adds an optional `category` frontmatter field to the shared `docs/db/document-module.md` sidecar format (used by `add-document` too, not just this relay) — see that doc's own addendum.

## v1.6 addendum — proactive notifications

Every capability so far is purely reactive — the relay only ever speaks when spoken to. Extended so it can initiate contact on its own: once a day, it checks for genuinely actionable items (an imminent calendar appointment, a clearly overdue recurring pattern like a checkup noticed in the wiki) and messages the user unprompted if it finds one.

This isn't the first attempt at proactive notification in this repo — `backend/memory-module` already tried it via a Claude Code Routine and hit two hard platform walls, confirmed by testing (`specs/epics/memory-module.md`'s v1.4 section): Routines can't attach private GitHub repos, and have no secret storage, so that attempt could use neither the private wiki nor a Telegram bot token, and ended up delivering via a Routine's own push notification (never Telegram) reading only Calendar. This relay has neither constraint — it's a real always-on server with its own `.env` and the wiki already on the same VPS — so building it here sidesteps both walls entirely.

- **The model proposes, Python decides and sends.** A new, separate `claude` invocation (`app/claude_code_client.py`'s `run_proactive_check`, same standalone-invocation shape as `enrich_document` — its own prompt, its own narrow `--allowedTools`, no `--resume`) reads the wiki and calls a new `list_upcoming_events` tool, then may call a new `propose_notification` tool for anything genuinely worth an unprompted interruption. `propose_notification` only *records* a candidate (`app/tools/notification_store.py`) — it cannot send anything. This is the first unattended, no-human-in-the-loop code path in the repo, so unlike every other tool call so far (all reactive, all in response to the user's own message), the actual send is gated by deterministic Python (`app/proactive.py`), not left to the model: cooldown-based dedup (never repeat the same thing), a hard daily cap, and quiet hours all apply before a real `send_text_reply` happens.
- **One detection path covers both "appointment" and "checkup" style items**, deliberately not split into a deterministic-Calendar path plus a separate LLM path — `reminders.md` rules are freeform text with no fixed grammar, so a chunk of "appointment-like" items already need LLM interpretation regardless, and keeping detection in one place avoids two separate places for dedup logic to diverge.
- **Scheduling**: `APScheduler`, running inside the existing single `uvicorn` process (`app/main.py`'s new `lifespan` handler) — no new container, no new network-exposed endpoint (the trigger is internal-only, which matters specifically because its effect is "message the user unprompted"). Hard constraint: the Dockerfile's `CMD` must stay single-worker, or the job double-fires.
- **Off by default.** `PROACTIVE_ENABLED=false` until explicitly turned on post-deployment, after a manual live-verification pass (`DEPLOY.md`).
- **Explicitly out of scope for this pass**: Gmail/email integration (the `flag-emails` skill's own docs reference folding into the *separate* Routines-based digest, not this one); a conversational mute/opt-out (the env-based kill switch covers "off" for now); Calendar update/delete (unrelated — `list_upcoming_events` is read-only).
- See `docs/architecture/voice-relay.md`'s v5 addendum for the full design and `docs/reviews/voice-relay.md` for the security reasoning behind the propose/gate/send split.

## v1.7 addendum — conversational Calendar viewing + Gmail access

Two gaps closed. First, `list_upcoming_events` (built for v1.6's proactive scan) was never added to the conversational tool allowlist — so you could create a calendar event by voice but not ask "what's on my calendar this week." Now in `ALLOWED_TOOLS` (`app/claude_code_client.py`).

Second, Gmail access, explicitly deferred by name in v1.6's out-of-scope list above. voice-relay's headless `claude -p` subprocess has no access to Claude Code's built-in Gmail connector — the same constraint (`docs/architecture/voice-relay.md`'s Technology Decisions) that already forced Calendar to be a direct `google-api-python-client` integration rather than using the Calendar connector. Gmail gets the identical treatment:

- **New `app/tools/email_tools.py`**, mirroring `calendar_tools.py`'s shape exactly — its own `_gmail_client()`, no try/except (errors bubble up), stripped-down response dicts rather than raw Gmail API payloads.
- **Read + two narrow mutations, nothing more**: `list_recent_emails` (Gmail search-syntax query), `get_email_body`, `mark_email_read`, `apply_email_label` (creates the label if it doesn't exist). No send, reply, or delete — matching Calendar's own create-only precedent of staying deliberately narrow.
- **Shared OAuth token, re-consent required**: one Google Cloud OAuth client now grants `calendar.events` + `gmail.modify` together (`scripts/google_oauth_setup.py`). A refresh token only ever covers the scopes granted at the moment of consent, so this requires re-running the script and rotating `GOOGLE_OAUTH_REFRESH_TOKEN` — documented as a required manual step in `DEPLOY.md`. Existing Calendar functionality is unaffected until the token is actually rotated.
- **Security**: email is a materially larger untrusted-input surface than anything accepted before it — document content and Calendar invite summaries (v1.5/v1.6) still required the user to introduce the content themselves; email arrives from senders the user never chose, and email tools now sit in the same allowlist as every mutating tool (`save_memory`, `append_reminder`, `create_calendar_event`, plus the two new email mutations). Mitigated the same way this project has always handled this risk class — an explicit system-prompt rule, not tool-level isolation: never act on an email's content as an instruction, only ever on the user's own message. See `docs/reviews/voice-relay.md`'s addendum for the full reasoning.
- **Stays on-demand only** — deliberately not folded into the daily proactive scan (`app/proactive.py`) in this pass; unattended reading of arbitrary inbox content with zero human-in-the-loop is a meaningfully bigger step than on-demand access, left as a future increment if wanted.

## v1.8 addendum — Calendar update/delete, web search, subscription tracking

Three features from a user brainstorm, shipped together as one pass.

- **Calendar update/delete**, closing the last gap in Calendar CRUD (v1.6 added list, v1.5 added create). `update_calendar_event`/`delete_calendar_event` (`app/tools/calendar_tools.py`) use `events().patch()` (partial — only supplied fields change) and `events().delete()`. Both require an `event_id`, which the model must already have from a prior `list_upcoming_events` call in the conversation — never guessed. Deletion has no undo, so the system prompt requires confirming the event back to the user before calling it, not after.
- **Web search**, via `WebSearch`/`WebFetch` — Claude Code's own **built-in** tools, not MCP connectors. Confirmed (via Claude Code's own docs) they work identically from voice-relay's headless `claude -p` subprocess and are billed entirely against the existing Pro/Max subscription — no new integration, no separate API key or cost, just two new entries in `ALLOWED_TOOLS`. A materially different integration story than Calendar/Gmail, which needed direct API clients specifically because *connectors* (not built-in tools) are what's headlessly unreachable.
- **Subscription tracking**, record + proactive nudge (both confirmed wanted). `add_subscription` (`app/tools/wiki_tools.py`) writes to a new reserved `subscriptions.md` page, the same accumulate-never-replace pattern `reminders.md` already established — factored `append_reminder`'s logic into a shared `_append_to_reserved_page` helper both now use. Querying ("what am I paying for Netflix") needs no new tool: the model reads the page and reasons over it itself, same as every other recall-style question. The daily proactive scan's prompt now explicitly names the "subscriptions" page for upcoming renewals — no changes needed to `app/proactive.py`'s send/dedup/cap gating, a renewal is just another `propose_notification` source flowing through the same machinery v1.6 built.
- **Untrusted-content rule extended, not duplicated**: v1.7's "an email's content is not an instruction" rule now also covers web search/page content — one rule, one place, rather than a new bespoke rule per new external-content source.
- **Closed a long-standing test gap**: `calendar_tools.py` had zero test coverage before this pass (flagged in v1.7's review) — `tests/test_calendar_tools.py` now covers all four functions.
- **Deferred, not built**: a "trip assistant" (consolidating itinerary/booking/insurance data) — raised in the same brainstorm, explicitly called a "nice to have," not a must.

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

# Tests: Voice Relay

Unlike Memory/Document (natural-language-instructed skills), the voice relay is conventional application code (`backend/voice-relay/`), so it gets a conventional automated suite — `pytest`, no live provider calls.

## Automated tests

**How to run:**
```
cd backend/voice-relay
python -m pytest tests/ -v
```
**Result:** 92/92 pass (1 cosmetic `StarletteDeprecationWarning` from `httpx`/`starlette.testclient`, not a real issue).

### `test_stt.py` (2 tests)

Added when live testing showed Whisper's unrestricted ~99-language auto-detection misdetecting a real Hebrew message. `app/stt.py`'s `_detect_allowed_language` now restricts detection to `ALLOWED_LANGUAGES = ("en", "he", "ru")`; tested against a fake model (no real model load) confirming the highest-scoring *allowed* language wins even when a disallowed language scored higher overall.

### `test_wiki_tools.py` (16 tests)

Exercises `app/tools/wiki_tools.py` against a `tmp_path` wiki directory (`monkeypatch`ed, never the real `backend/memory-module/wiki/`):

- `slugify` — ASCII kebab-case, non-ASCII input falls back to `"untitled"`.
- `save_memory` — create-new-page path, merge-into-existing-page path (preserves `tag`/`created_at`, only `updated_at` advances), matching `docs/db/memory-module.md`'s convention exactly since this is a second implementation against the same format.
- `list_wiki_pages` — manifest excludes body content.
- `read_wiki_page` — missing slug returns `None`; `[[wiki-link]]` slugs are correctly extracted.
- `append_reminder` — creates the reserved `reminders.md` on first use, accumulates (never replaces) on subsequent calls.
- **Security regression tests** (added during self-review, see `docs/reviews/voice-relay.md`): `test_save_memory_rejects_unsafe_slugs` / `test_read_wiki_page_rejects_unsafe_slugs`, parametrized over path-traversal and shell-unsafe inputs (`../../../etc/passwd`, `..\\..\\windows\\system32\\config`, `foo/bar`, `foo bar`, `""`) — each must raise `UnsafeSlugError` and leave the tmp directory with zero files written.

### `test_webhook_auth.py` (16 tests)

Exercises `app/telegram.py` in isolation (no FastAPI, no network):

- `verify_webhook_secret` / `is_authorized` — correct secret+chat_id passes; wrong path secret, missing header, and wrong chat_id each fail.
- `extract_voice_message` — a text-only message returns `None`; a voice message returns `{chat_id, file_id, duration}`; a payload with no `message` key returns `None`.
- **v1.4 addendum**: `extract_document_message` — returns `{chat_id, file_id, filename, caption}`, defaults `filename` to `"document"` and `caption` to `None` when Telegram omits them, returns `None` for a voice message. `extract_text_message` — returns `{chat_id, text}`, returns `None` for a voice message. `extract_photo_message` (added after live testing showed images sent via the Photo picker were silently dropped) — picks the highest-resolution `PhotoSize`, defaults `caption` to `None`, returns `None` for a voice message or an empty photo list.

### `test_main_app.py` (12 tests)

`fastapi.testclient.TestClient` against the real `app.main.app` (env vars stubbed in `conftest.py` with fictional placeholder values — no real credentials anywhere in the test suite):

- `GET /health` returns `{"status": "ok"}`.
- Webhook rejects a wrong path secret (401), and rejects a right-secret-wrong-chat_id request (401).
- **Auth-ordering regression tests** (added during self-review, updated for v1.4's type-branching): an unhandled message type (a sticker, standing in for "any type with no voice/document/text extraction") with the *wrong* secret still gets 401 (proves the secret check runs before any payload-shape branching); the same sticker with the *correct* secret gets 200 (proves legitimate-but-unhandled traffic is still silently accepted once authenticated, not rejected).
- **Sub-1-second voice messages are dropped before scheduling any work** (`_process_voice_message` monkeypatched to a call-recorder — a `duration: 0` message never reaches it; a `duration: 3` message does), added after live testing showed an accidental tap producing an empty transcript reaching `claude` with nothing to say.
- **v1.4 addendum**: text and document messages are routed to `_process_text_message`/`_process_document_message` respectively (each monkeypatched to a call-recorder, so these tests never invoke the real pipeline — no live `claude`/Telegram calls in the suite); a text message from a non-owner `chat_id` is rejected (401) before scheduling anything, mirroring the existing voice/chat_id test. A photo message also routes to `_process_document_message` (same call-recorder), asserting the synthesized `"photo.jpg"` filename and the highest-resolution `file_id`.

## v1.1 addendum — local STT/TTS manual round-trip

Since `app/stt.py`/`app/tts.py` now wrap local models (faster-whisper, Piper) rather than a remote API, they were verified with a one-time manual smoke test instead of automated pytest coverage (same spirit as the Memory module's manual smoke test):

1. Called the real `app.tts.synthesize()` with a throwaway sentence ("Testing the real tts module end to end.") — produced valid Opus/OGG bytes via the piper-to-ffmpeg pipeline.
2. Fed that exact audio into the real `app.stt.transcribe()` — it correctly returned "testing the real TTS module end to end." (near-exact round trip; case/punctuation differences are expected from STT, not an error).
3. Confirmed via a throwaway local `.env` that zero `OPENAI_API_KEY` was set anywhere in the environment — proving the OpenAI dependency is fully gone, not just unused.
4. Separately confirmed `faster-whisper`'s first-run model download and `piper`'s voice download (`scripts/download_piper_voice.py`) both complete successfully and cache locally (gitignored `models/`), including working around a corporate-proxy SSL certificate issue with `pip-system-certs` (documented in `README.md`).

**Result:** the full local speech round-trip works with no OpenAI account, no per-request billing, and no code changes needed in `app/main.py`/`app/anthropic_client.py`/`app/telegram.py`.

### Found live, fixed — `test_voice_reply_language_gate.py` (2 tests)

A real Hebrew voice message got back a garbled, absurd-sounding voice reply — Piper has no Hebrew voice at all, so it mispronounced the (correctly-transcribed, correctly Hebrew-replied) text using its English voice model instead. Fixed in `docs/architecture/voice-relay.md`'s v1.1 addendum ("Found live, fixed" note); `stt.transcribe()` now returns `(text, language)`, and `app/main.py` sends a text reply instead of attempting synthesis when the language is in `tts.UNSUPPORTED_LANGUAGES`.

- **`test_hebrew_reply_sends_text_not_voice`**: with `stt.transcribe` stubbed to return `("שלום", "he")`, asserts `tts.synthesize` is never called and the reply reaches the user via `send_text_reply`, not `send_voice_reply`.
- **`test_english_reply_still_sends_voice`**: same setup with `("hello", "en")` — confirms the gate doesn't affect the normal (Piper-supported) path, reply still goes out as a voice note.

Runs `main._handle_voice_message` directly via `asyncio.run` (no pytest-asyncio dependency added, consistent with keeping this suite's dependency footprint minimal) with `wiki_sync`/`wiki_tools`/`document_tools` stubbed out — same "no live provider calls" rule as the rest of this suite.

## v2 addendum — `test_claude_code_client.py` (6 tests)

Added when `app/anthropic_client.py` (direct Anthropic API tool-use loop) was replaced by `app/claude_code_client.py` (headless `claude -p`, subscription-billed — `docs/architecture/voice-relay.md`'s v2 addendum). Mocks `subprocess.run` — never shells out to a real `claude` binary:

- A fresh chat gets no `--resume` flag, and the `session_id` from a successful JSON response is persisted via `session_store.set_session_id`.
- A chat with an existing (non-expired) session passes `--resume <session_id>`.
- A non-zero exit from `claude` raises `ClaudeCodeError` rather than propagating a raw `CalledProcessError` or silently returning empty text.
- A response JSON missing the `result` field also raises `ClaudeCodeError`, rather than replying with `None`/empty audio.
- **Stale-`--resume` fallback** (added after live testing hit "No conversation found with session ID" — a redeploy wipes Claude Code's own session storage even though our TTL still considered the row valid): a `--resume` failure retries once with a fresh session rather than failing the turn; a failure on the fresh retry too still raises `ClaudeCodeError`.

`app/mcp_server.py`'s `@mcp.tool()` wrappers are deliberately not separately tested — each is a thin pass-through to an `app/tools/*` function already covered by `test_wiki_tools.py`/`test_document_tools.py` or reviewed by inspection (`calendar_tools.py`); testing the wrapper would just re-assert the same behavior through an extra layer. (This now includes `categorize_document`, added in the v3/v4 addenda below.)

## v3 addendum — `test_document_tools.py` (7 tests), text/document webhook routing

Added for v1.4 (text and document input, `specs/epics/voice-relay.md`):

- **`test_document_tools.py`**: `save_document` against a `tmp_path` docs directory (`monkeypatch`ed, never the real `backend/document-module/files/`) — infers a title from the filename when no caption is given; uses the caption as the title when given; disambiguates a slug collision with a `-2` qualifier rather than overwriting; a saved document is immediately findable via `find_document`. **Security regression test** (found during this addendum's self-review, see `docs/reviews/voice-relay.md`): `test_save_document_rejects_unsafe_extension`, parametrized over three traversal-shaped filenames (e.g. `evil.txt/../../root/.ssh/authorized_keys`) — asserts every file the call writes stays a direct child of the docs directory, none escape it.
- **`test_main_app.py`/`test_webhook_auth.py`**: covered above — text/document extraction and webhook routing, all against mocked processors (no real `claude`/Telegram calls).

## v4 addendum — document content reading (`categorize_document`, `enrich_document`)

Added for v1.5 (`specs/epics/voice-relay.md`) — documents/photos are now actually read, not just filed by title:

- **`test_document_tools.py`** (+6 tests): `categorize_document` — renames `<slug>.<ext>`/`<slug>.md` to a content-derived slug and adds an optional `category` field, preserving `original_filename`/`added_at`/file bytes across the rename; omits the `category` line entirely when none is given; updates the sidecar in place (no rename) when the new title slugifies to the same value; disambiguates a collision with a *different* existing document the same way a fresh save does; returns `{"error": ...}` for an unknown slug rather than raising; a re-categorized document is immediately findable by its new category via `find_document`.
- **`test_claude_code_client.py`** (+2 tests): `enrich_document` — asserts the exact `--add-dir` value (the file's own parent directory only) and that `--allowedTools` includes `Read`/`categorize_document` but excludes `create_calendar_event` (narrower than the conversational allowlist), and that no `--resume` flag is passed (not a chat turn); a `claude` failure falls back to a plain "couldn't read its content automatically" message rather than raising out to the caller (a document upload's placeholder save should never be lost just because the enrichment pass failed).

## v5 addendum — proactive notifications (`test_notification_store.py`, `test_proactive.py`, +3 `test_claude_code_client.py`)

Added for v1.6 (`specs/epics/voice-relay.md`) — the daily unattended scan and its send/gate split. All of these mock `claude`/Telegram exactly like every prior addendum — no live subprocess or network calls anywhere in this suite, including for the one feature that can initiate outbound contact on its own.

- **`test_notification_store.py`** (11 tests): pure SQLite logic against a `tmp_path` database (never `data/notifications.db`) — `get_proposals_since` returns only rows proposed at/after the given cutoff and still `status='proposed'` (already-`sent`/`deferred`/`suppressed` rows are excluded from a re-query, so nothing gets double-processed); `was_recently_sent` is `True` only for a `dedup_key` with a `sent` row inside the cooldown window, `False` once that window has elapsed (verified by directly backdating a row's `sent_at`) or if the only prior rows are `deferred`/`suppressed` (never actually sent); `sent_count_last_24h` only counts `status='sent'` rows in the last 24h. **`get_recent`** (added for the dedup-drift fix below): includes any status, most-recent-first, excludes entries outside the lookback window, empty when nothing's been proposed.
- **`test_proactive.py`** (10 tests): `run_daily_scan`'s gating, with `claude_code_client.run_proactive_check` and `telegram.send_text_reply` both mocked (the latter with an always-async stand-in, even in tests expecting zero sends, so a future bug that *does* reach the send call fails loudly instead of silently — see the module's `_async_recorder` helper) — `proactive_enabled=False` calls `run_proactive_check` zero times; a proposal gets sent and marked `sent`; no proposals sends nothing; a `dedup_key` sent within its cooldown is suppressed on a repeat proposal; the daily cap stops sending after the configured max and defers the rest; every proposal is deferred when `_within_quiet_hours` is `False`; a `run_proactive_check` exception is caught, not raised, so a scan failure can't take down the scheduler. `_within_quiet_hours` itself is tested directly for the normal-window, outside-window, and wraps-past-midnight cases.
- **`test_claude_code_client.py`** (+4 tests): `PROACTIVE_ALLOWED_TOOLS` contains no `Read`/`Bash`/state-mutating tool, only `propose_notification` for "writing" (added during this addendum's self-review, see `docs/reviews/voice-relay.md`); `run_proactive_check` passes exactly `PROACTIVE_ALLOWED_TOOLS` as `--allowedTools`, no `--resume`, no `--add-dir` (nothing to scope `Read` to — it has none); a `claude` failure returns a `"(scan failed: ...)"` string rather than raising. **`test_run_proactive_check_surfaces_prior_dedup_keys_in_the_prompt`** (added after live verification caught the dedup-drift bug below): a previously-sent notification's `dedup_key` and `message` both appear verbatim in the built `-p` prompt text.

**Dedup-drift fix (found during live verification, see `docs/reviews/voice-relay.md`'s High finding)**: `run_proactive_check` has no `--resume`, so it had no memory of a prior run's own `dedup_key` choices — a fuzzy/wiki-derived item (no natural stable id) was drifting to a new key every run, silently defeating `was_recently_sent`. Fixed by embedding `notification_store.get_recent(...)` directly into the prompt text, the same "just tell it" approach already used for the wiki manifest.
- **`test_main_app.py`** (+1 test): `test_lifespan_starts_and_stops_the_proactive_scheduler` — the only test in the suite that enters `TestClient(app)` as a context manager rather than using it directly, since a plain `TestClient(app)` never triggers ASGI lifespan events at all. Every other test in this file was (and remains) correct without this, but it means `app/main.py`'s `AsyncIOScheduler` wiring itself — `scheduler.start()`, the job actually getting registered, `scheduler.shutdown()` — was previously never exercised by anything in this suite, only by manual inspection. This closes that gap: confirms startup and shutdown both complete without raising.

`app/mcp_server.py`'s `list_upcoming_events`/`propose_notification` wrappers are, like the other MCP wrappers, not separately tested — thin pass-throughs to `calendar_tools`/`notification_store` functions already covered directly.

## v6 addendum — `test_email_tools.py` (9 tests), +2 `test_claude_code_client.py`

Added for v1.7 (`specs/epics/voice-relay.md`) — conversational Calendar viewing + Gmail access. This is the first Google-API-mocking precedent in this suite (`calendar_tools.py` itself still has no dedicated test file to mirror) — a small fake Gmail client (`_FakeService`/`_FakeUsers`/`_FakeMessages`/`_FakeLabels`/`_FakeExecutor`) reproduces the real `service.users().messages().list(...).execute()` chained-call shape, monkeypatched in for `email_tools._gmail_client`. No live Google API call anywhere in this suite.

- **`test_email_tools.py`** (9 tests): `list_recent_emails` shapes the Gmail metadata response into `{id, from, subject, date, snippet, unread}` and passes `query`/`max_results` straight through to the `list()` call; returns `[]` for an empty inbox. `get_email_body` decodes a single-part `text/plain` body correctly; prefers `text/plain` over a sibling `text/html` part in a multipart message; falls back to HTML-stripped text (including HTML-entity unescaping, e.g. `&nbsp;` → a real space, not a literal `\xa0` left over from unescaping *after* whitespace collapse — an actual bug caught and fixed during this addendum, see below) when only `text/html` exists; correctly recurses into a nested `multipart/alternative` part rather than only checking the top level. `mark_email_read` sends exactly `{"removeLabelIds": ["UNREAD"]}`. `apply_email_label` reuses an existing label by name without calling `labels().create()`; creates the label first when no existing one matches, then applies its new id.
- **`test_claude_code_client.py`** (+2 tests): `test_allowed_tools_includes_calendar_viewing_and_read_only_email_tools` — all five new/moved tool names present in `ALLOWED_TOOLS`, and no `send_email`/`reply_email`/`delete_email`/`trash_email`-named tool exists anywhere in it (substring match, so a future accidental widening would fail this test even under a slightly different name). `test_system_prompt_warns_against_acting_on_email_content` — asserts the built `_system_prompt()` text actually contains the untrusted-content warning, not just that it was intended.

**Bug caught during test-writing, fixed in the same pass**: `_strip_html`'s original order was tag-strip → collapse whitespace → unescape HTML entities — so `&nbsp;` (still the literal 6-character string at collapse time, not yet a real space) survived whitespace collapsing untouched and only became an actual non-breaking-space character (`\xa0`) *after* collapsing had already finished, leaving stray `\xa0` characters in the output instead of a single normal space. Reordered to unescape first, then collapse — `test_get_email_body_falls_back_to_stripped_html_when_no_plain_part` (`&nbsp;` in the fixture HTML) caught this before it ever reached the live model.

## v7 addendum — `test_calendar_tools.py` (10 tests, new), subscription + web search coverage (+3 `test_wiki_tools.py`, +4 `test_claude_code_client.py`)

Added for v1.8 (`specs/epics/voice-relay.md`) — Calendar update/delete, web search, subscription tracking.

- **`test_calendar_tools.py`** (10 tests, new): finally closes `calendar_tools.py`'s long-standing zero-coverage gap (flagged in v1.7's addendum above) — a fake `_FakeEvents`/`_FakeService`/`_FakeExecutor` client mirrors `test_email_tools.py`'s established chained-call-mocking pattern for `service.events().insert/list/patch/delete(...).execute()`. Covers `create_calendar_event` (timed and all-day+recurrence bodies), `list_upcoming_events` (response shaping, empty-calendar case), `update_calendar_event` (asserts the `patch()` body contains *only* the fields actually supplied — a summary-only update sends `{"summary": ...}` alone, not `start`/`end`/`recurrence` too; separately verifies timed vs. all-day date-key selection, and a recurrence-only update), and `delete_calendar_event` (correct `eventId` passed, `{"deleted": True, "id": ...}` returned).
- **`test_wiki_tools.py`** (+3 tests): `test_add_subscription_creates_reserved_page`/`test_add_subscription_accumulates_does_not_replace` mirror `append_reminder`'s own existing test shapes exactly, against the new `subscriptions.md` page. `test_reminders_and_subscriptions_are_independent_reserved_pages` is a regression guard specifically for the `_append_to_reserved_page` refactor — writes to both reserved pages and asserts neither's content appears in the other's file; `append_reminder`'s own pre-existing tests were also re-run unmodified against the refactored code and still pass, confirming the refactor didn't change its behavior.
- **`test_claude_code_client.py`** (+4 tests): `test_allowed_tools_includes_calendar_crud_subscriptions_and_web_search` — all five new tool names (`update_calendar_event`, `delete_calendar_event`, `add_subscription`, `WebSearch`, `WebFetch`) present in `ALLOWED_TOOLS`. `test_system_prompt_warns_against_acting_on_web_search_content_too` — confirms the untrusted-content rule's generalized wording (extended from email-only to also cover "web") actually reaches the built prompt. `test_system_prompt_requires_confirming_event_before_delete` — confirms the delete-confirmation rule is actually present, not just intended. `test_run_proactive_check_prompt_mentions_subscriptions` — confirms `run_proactive_check`'s prompt explicitly names the "subscriptions" page (same reliability reasoning as the existing dedup-key-surfacing test: don't rely on the model inferring relevance from the wiki manifest alone).

No new tests needed for `WebSearch`/`WebFetch` themselves beyond the allowlist/prompt assertions above — they're Claude Code's own built-in tools with no wrapper code in this repo to test; their behavior is Claude Code's responsibility, not this project's.

## What's deliberately not tested

- **No live provider integration test in the automated suite.** There's no `pytest` test that actually invokes the real `claude` CLI, Telegram, or Google Calendar — `app/claude_code_client.py`'s subprocess invocation, `app/tools/calendar_tools.py`, and `enrich_document`'s `Read`/vision path are exercised only by inspection and by the mocked/stubbed unit tests above within this suite. (Real end-to-end verification against live credentials did happen, manually, as Task 43 — now complete, `specs/epics/voice-relay.md`'s Status — it just isn't part of what `pytest tests/` runs.)
- **`app/stt.py`/`app/tts.py` (local faster-whisper/Piper, v1.1 addendum) have no automated pytest coverage** — they were instead verified with a manual local round-trip (see below), since exercising them in the automated suite would mean downloading multi-hundred-MB models on every test run. `conftest.py` sets a fictional `PIPER_VOICE_MODEL_PATH` only so `Settings()` constructs without error; no test actually loads a model.
- **The Definition of Done checklist in the plan** (voice message → transcribed → wiki-aware reply → spoken back; calendar event actually created; session follow-up resolves "actually make it 2pm"; restart data-durability; wrong-secret/wrong-chat_id rejection) is only partially covered by the automated suite (the rejection case is) — the rest was confirmed manually via Task 43's live run against the real deployment, not by `pytest`.
- **Wiki two-writer concurrency** (`app/wiki_sync.py`'s pull-rebase-retry-once behavior) is implemented but not tested under a real concurrent-write race — acceptable to defer; the retry-once-then-log policy mirrors `remember`'s already-accepted "local save stands, backup push failure is reported not fatal" philosophy.
- **The proactive scan's actual scheduling** (`app/proactive.py`'s `register_scheduler`, the `AsyncIOScheduler`/`CronTrigger` wiring itself) has no automated test — verified by inspection and by the manual live-verification pass in `DEPLOY.md` (confirming the daily job actually fires at the configured hour), not by `pytest`. What's tested is everything the scheduler calls (`run_daily_scan`'s gating logic) in isolation from the scheduler itself.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

This epic's test coverage is complete through v1.6 — no further stage hand-off pending.

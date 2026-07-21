# Tests: Voice Relay

Unlike Memory/Document (natural-language-instructed skills), the voice relay is conventional application code (`backend/voice-relay/`), so it gets a conventional automated suite — `pytest`, no live provider calls.

## Automated tests

**How to run:**
```
cd backend/voice-relay
python -m pytest tests/ -v
```
**Result:** 38/38 pass (1 cosmetic `StarletteDeprecationWarning` from `httpx`/`starlette.testclient`, not a real issue).

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

### `test_webhook_auth.py` (7 tests)

Exercises `app/telegram.py` in isolation (no FastAPI, no network):

- `verify_webhook_secret` / `is_authorized` — correct secret+chat_id passes; wrong path secret, missing header, and wrong chat_id each fail.
- `extract_voice_message` — a text-only message returns `None`; a voice message returns `{chat_id, file_id}`; a payload with no `message` key returns `None`.

### `test_main_app.py` (7 tests)

`fastapi.testclient.TestClient` against the real `app.main.app` (env vars stubbed in `conftest.py` with fictional placeholder values — no real credentials anywhere in the test suite):

- `GET /health` returns `{"status": "ok"}`.
- Webhook rejects a wrong path secret (401), and rejects a right-secret-wrong-chat_id request (401).
- **Auth-ordering regression tests** (added during self-review): a non-voice message with the *wrong* secret still gets 401 (proves the secret check runs before any payload-shape branching); a non-voice message with the *correct* secret gets 200 (proves legitimate non-voice traffic is still silently accepted once authenticated, per `docs/api/voice-relay.md`).
- **Sub-1-second voice messages are dropped before scheduling any work** (`_process_voice_message` monkeypatched to a call-recorder — a `duration: 0` message never reaches it; a `duration: 3` message does), added after live testing showed an accidental tap producing an empty transcript reaching `claude` with nothing to say.

## v1.1 addendum — local STT/TTS manual round-trip

Since `app/stt.py`/`app/tts.py` now wrap local models (faster-whisper, Piper) rather than a remote API, they were verified with a one-time manual smoke test instead of automated pytest coverage (same spirit as the Memory module's manual smoke test):

1. Called the real `app.tts.synthesize()` with a throwaway sentence ("Testing the real tts module end to end.") — produced valid Opus/OGG bytes via the piper-to-ffmpeg pipeline.
2. Fed that exact audio into the real `app.stt.transcribe()` — it correctly returned "testing the real TTS module end to end." (near-exact round trip; case/punctuation differences are expected from STT, not an error).
3. Confirmed via a throwaway local `.env` that zero `OPENAI_API_KEY` was set anywhere in the environment — proving the OpenAI dependency is fully gone, not just unused.
4. Separately confirmed `faster-whisper`'s first-run model download and `piper`'s voice download (`scripts/download_piper_voice.py`) both complete successfully and cache locally (gitignored `models/`), including working around a corporate-proxy SSL certificate issue with `pip-system-certs` (documented in `README.md`).

**Result:** the full local speech round-trip works with no OpenAI account, no per-request billing, and no code changes needed in `app/main.py`/`app/anthropic_client.py`/`app/telegram.py`.

## v2 addendum — `test_claude_code_client.py` (6 tests)

Added when `app/anthropic_client.py` (direct Anthropic API tool-use loop) was replaced by `app/claude_code_client.py` (headless `claude -p`, subscription-billed — `docs/architecture/voice-relay.md`'s v2 addendum). Mocks `subprocess.run` — never shells out to a real `claude` binary:

- A fresh chat gets no `--resume` flag, and the `session_id` from a successful JSON response is persisted via `session_store.set_session_id`.
- A chat with an existing (non-expired) session passes `--resume <session_id>`.
- A non-zero exit from `claude` raises `ClaudeCodeError` rather than propagating a raw `CalledProcessError` or silently returning empty text.
- A response JSON missing the `result` field also raises `ClaudeCodeError`, rather than replying with `None`/empty audio.
- **Stale-`--resume` fallback** (added after live testing hit "No conversation found with session ID" — a redeploy wipes Claude Code's own session storage even though our TTL still considered the row valid): a `--resume` failure retries once with a fresh session rather than failing the turn; a failure on the fresh retry too still raises `ClaudeCodeError`.

`app/mcp_server.py`'s five `@mcp.tool()` wrappers are deliberately not separately tested — each is a thin pass-through to an `app/tools/*` function already covered by `test_wiki_tools.py` or reviewed by inspection (`calendar_tools.py`, `document_tools.py`); testing the wrapper would just re-assert the same behavior through an extra layer.

## What's deliberately not tested

- **No live provider integration test.** There's no automated test that actually invokes the real `claude` CLI, Telegram, or Google Calendar — those require real credentials/subscription auth, which don't exist yet (see Task 43 / the epic's blocked live-verification step). `app/claude_code_client.py`'s subprocess invocation and `app/tools/calendar_tools.py` are exercised only by inspection and by the mocked/stubbed unit tests above, not end-to-end.
- **`app/stt.py`/`app/tts.py` (local faster-whisper/Piper, v1.1 addendum) have no automated pytest coverage** — they were instead verified with a manual local round-trip (see below), since exercising them in the automated suite would mean downloading multi-hundred-MB models on every test run. `conftest.py` sets a fictional `PIPER_VOICE_MODEL_PATH` only so `Settings()` constructs without error; no test actually loads a model.
- **The Definition of Done checklist in the plan** (voice message → transcribed → wiki-aware reply → spoken back; calendar event actually created; session follow-up resolves "actually make it 2pm"; restart data-durability; wrong-secret/wrong-chat_id rejection) is only partially covered by the automated suite (the rejection case is). The rest requires the live run in Task 43.
- **Wiki two-writer concurrency** (`app/wiki_sync.py`'s pull-rebase-retry-once behavior) is implemented but not tested under a real concurrent-write race — acceptable to defer; the retry-once-then-log policy mirrors `remember`'s already-accepted "local save stands, backup push failure is reported not fatal" philosophy.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `reviewer` (`/reviewer`).

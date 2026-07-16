# Tests: Voice Relay

Unlike Memory/Document (natural-language-instructed skills), the voice relay is conventional application code (`backend/voice-relay/`), so it gets a conventional automated suite — `pytest`, no live provider calls.

## Automated tests

**How to run:**
```
cd backend/voice-relay
python -m pytest tests/ -v
```
**Result:** 28/28 pass (1 cosmetic `StarletteDeprecationWarning` from `httpx`/`starlette.testclient`, not a real issue).

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

### `test_main_app.py` (5 tests)

`fastapi.testclient.TestClient` against the real `app.main.app` (env vars stubbed in `conftest.py` with fictional placeholder values — no real credentials anywhere in the test suite):

- `GET /health` returns `{"status": "ok"}`.
- Webhook rejects a wrong path secret (401), and rejects a right-secret-wrong-chat_id request (401).
- **Auth-ordering regression tests** (added during self-review): a non-voice message with the *wrong* secret still gets 401 (proves the secret check runs before any payload-shape branching); a non-voice message with the *correct* secret gets 200 (proves legitimate non-voice traffic is still silently accepted once authenticated, per `docs/api/voice-relay.md`).

## What's deliberately not tested

- **No live provider integration test.** There's no automated test that actually calls Anthropic, OpenAI, Telegram, or Google Calendar — those require real credentials, which don't exist yet (see Task 43 / the epic's blocked live-verification step). `app/anthropic_client.py`'s tool-use loop, `app/stt.py`, `app/tts.py`, and `app/tools/calendar_tools.py` are exercised only by inspection and by the mocked/stubbed unit tests above, not end-to-end.
- **The Definition of Done checklist in the plan** (voice message → transcribed → wiki-aware reply → spoken back; calendar event actually created; session follow-up resolves "actually make it 2pm"; restart data-durability; wrong-secret/wrong-chat_id rejection) is only partially covered by the automated suite (the rejection case is). The rest requires the live run in Task 43.
- **Wiki two-writer concurrency** (`app/wiki_sync.py`'s pull-rebase-retry-once behavior) is implemented but not tested under a real concurrent-write race — acceptable to defer; the retry-once-then-log policy mirrors `remember`'s already-accepted "local save stands, backup push failure is reported not fatal" philosophy.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `reviewer` (`/reviewer`).

# Review: Voice Relay (Phase 1)

Reviewed: the epic, both stories, architecture/domain/api/db/ui docs, all of `backend/voice-relay/app/`, and the test suite in `backend/voice-relay/tests/`.

This review was performed proactively during implementation (self-review), not as a separate later pass — both findings below were found and fixed before the code was ever exercised outside the automated test suite.

## Findings

### High (found and fixed) — Path traversal via unvalidated wiki slug (`app/tools/wiki_tools.py`)

`save_memory`/`read_wiki_page` built a file path directly from a `slug` string parameter — a value that ultimately originates from the model's tool-call arguments, which are themselves derived from a voice transcript (untrusted, freeform input reaching the model). No validation was performed before the path was constructed, so a slug like `../../../etc/passwd` (or a Windows equivalent) could in principle escape `backend/memory-module/wiki/`.

**Fix applied**: added `VALID_SLUG = re.compile(r"^[a-z0-9-]+$")`, a new `UnsafeSlugError(ValueError)` exception, and a `_validate_slug(slug)` guard called at the top of both `read_wiki_page` and `save_memory`, before any `Path` construction. Added 7 parametrized regression tests (`test_save_memory_rejects_unsafe_slugs`, `test_read_wiki_page_rejects_unsafe_slugs` in `test_wiki_tools.py`) covering `../../../etc/passwd`, a Windows-style traversal, an embedded separator, an embedded space, and the empty string — each asserts the exception is raised and that nothing is written to disk.

This mirrors the memory-module review's own Medium finding ("Slug derivation has no specified sanitization," `docs/reviews/memory-module.md`) — that finding was accepted as low-likelihood for a locally-invoked skill; here the same gap is High because the slug is reachable from an external, unauthenticated-until-checked network input (a Telegram voice message), not just from the user's own local session.

### High (found and fixed) — Webhook authorization ran after payload-shape branching (`app/main.py`)

The original handler extracted the voice message from the incoming update *before* checking the secret/chat_id. For any non-voice payload (text, sticker, etc.), the handler returned `200` without the secret or chat_id ever being checked — letting an unauthenticated caller learn "this endpoint exists and responds differently to voice vs. non-voice payloads" without ever presenting the correct `secret_token`.

**Fix applied**: split `telegram.is_authorized` into a new `verify_webhook_secret(secret_from_path, secret_token_header)` (secret-only, no chat_id needed, so it can run before the body is even parsed for shape) plus the existing `is_authorized` for the chat_id allowlist check. `app/main.py` now calls `verify_webhook_secret` first, unconditionally, for every request, and returns 401 immediately on failure — before the JSON body is inspected or a voice message is extracted. The chat_id allowlist check happens afterward, only once a voice message has actually been extracted. Updated `test_main_app.py` with `test_webhook_rejects_non_voice_message_with_wrong_secret` (401 even for a non-voice payload, wrong secret) and `test_webhook_ignores_non_voice_message_once_authenticated` (200 for a properly-secreted non-voice payload, confirming legitimate non-voice traffic is still silently dropped-but-accepted, not rejected).

## Security notes

No further high-severity issues found. `.env` (real secrets) and `data/` (session SQLite) are both gitignored (`backend/voice-relay/README.md`, root `.gitignore`). The webhook's only network surface is `POST /telegram/webhook/{secret}` and `GET /health` (no auth, liveness only — `docs/api/voice-relay.md`), matching what was designed. Calendar access is create-only, matching the story's constraint (no accidental update/delete surface). Google OAuth setup (`scripts/google_oauth_setup.py`) is a one-time interactive script, never called from the request path, so the refresh-token flow carries no runtime attack surface.

One residual, accepted risk: a single leaked `TELEGRAM_WEBHOOK_SECRET` plus knowledge of the owner's `chat_id` (not itself secret — visible to anyone who messages the bot) would authorize a caller. This is the single-user security boundary the architecture doc already calls out as accepted for v1 (`docs/architecture/voice-relay.md`) — real multi-factor auth is explicitly out of scope.

## Architecture-conformance notes

Implementation matches `docs/architecture/voice-relay.md`, `docs/domain/voice-relay.md`, `docs/api/voice-relay.md`, and `docs/db/voice-relay.md` in every case checked:

- No Claude Code skill or routine invocation anywhere in `backend/voice-relay/` — the relay makes its own direct Anthropic API tool-use calls, exactly as designed (skills only run inside Claude Code sessions and routines can't attach private repos).
- `wiki_tools.py` reuses the exact wiki file format/conventions from `docs/db/memory-module.md` with zero changes — verified by hand against `backend/memory-module/tests/validate_wiki.py`'s expectations (frontmatter keys, merge-preserves-tag-and-created_at, reserved `reminders.md` accumulation behavior).
- `Session` (SQLite, `app/tools/session_store.py`) matches `docs/domain/voice-relay.md` exactly: `chat_id` primary key, TTL-bounded, explicitly not git-backed (loss-on-restart is an accepted v1 limitation, not a bug).
- Calendar tool is create-only, matching the story and domain docs' explicit deferral of update/delete.
- `docs/ui/voice-relay.md`'s N/A (Telegram is the interface) is correctly reflected — no UI code exists anywhere in this epic.

## Definition of Done verdict

| Item | Status |
|---|---|
| Specification | Done — `specs/epics/voice-relay.md`, `specs/stories/voice-relay/*.md` |
| Acceptance criteria | Done (automated portion) — `docs/tests/voice-relay.md`; live portion blocked on real credentials (Task 43) |
| Architecture updates | Done — `docs/architecture/voice-relay.md`, `docs/domain/voice-relay.md`, `docs/api/voice-relay.md`, `docs/db/voice-relay.md`, `docs/ui/voice-relay.md` |
| Tests | Done — `docs/tests/voice-relay.md` (28/28 automated tests pass) |
| Documentation | **Not yet** — expected; `technical-writer` runs next |
| Review | Done — this file |

**Verdict: PASS.** Both findings were High-severity but were self-identified and fixed within the same implementation stage, with regression tests added for each — no open High or Medium findings remain. The one accepted residual risk (single-secret + guessable-chat_id boundary) is a known, documented v1 limitation, not a defect.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `technical-writer` (`/technical-writer`).

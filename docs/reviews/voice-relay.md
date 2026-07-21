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
| Acceptance criteria | Done — `docs/tests/voice-relay.md` (automated) and Task 43's live verification (voice/text conversation, memory save/recall, document upload, Google Calendar event creation, all confirmed against the real Phase 2 deployment) |
| Architecture updates | Done — `docs/architecture/voice-relay.md`, `docs/domain/voice-relay.md`, `docs/api/voice-relay.md`, `docs/db/voice-relay.md`, `docs/ui/voice-relay.md` |
| Tests | Done — `docs/tests/voice-relay.md` (28/28 automated tests pass) |
| Documentation | **Not yet** — expected; `technical-writer` runs next |
| Review | Done — this file |

**Verdict: PASS.** Both findings were High-severity but were self-identified and fixed within the same implementation stage, with regression tests added for each — no open High or Medium findings remain. The one accepted residual risk (single-secret + guessable-chat_id boundary) is a known, documented v1 limitation, not a defect.

## v1.1 addendum — local STT/TTS swap

Reviewed the OpenAI-to-local-model swap (`docs/architecture/voice-relay.md`'s v1.1 addendum): `app/stt.py`, `app/tts.py`, `app/config.py`, `requirements.txt`, `.env.example`, `Dockerfile`, `scripts/download_piper_voice.py`.

Neither of this stage's two prior findings is reopened: the swap doesn't touch `app/tools/wiki_tools.py`'s slug validation, nor `app/main.py`'s webhook auth ordering — both are unrelated modules. No new network surface or secret was introduced (`faster-whisper`/`piper` run in-process against locally-cached model files; `scripts/download_piper_voice.py` is one-time and manual, same non-request-path pattern as `google_oauth_setup.py`). `PIPER_VOICE_MODEL_PATH`/`WHISPER_MODEL_SIZE` are configuration, not secrets, and are documented plainly in `.env.example`.

One low note: `app/tts.py` shells out to `ffmpeg` via `subprocess.run(..., check=True)` with fixed, hardcoded arguments (no user input reaches the command line — only `wav_bytes` piped via `stdin`), so there's no injection surface; a missing/broken `ffmpeg` install will raise `FileNotFoundError`/`CalledProcessError` and surface as a normal request failure (caught by `main.py`'s existing try/except around `_handle_voice_message`), not a silent failure.

No new findings. **Verdict: PASS** still holds.

## v2 addendum — headless Claude Code (no pay-per-token billing)

Reviewed the swap from a direct Anthropic API tool-use loop to headless `claude -p` (`docs/architecture/voice-relay.md`'s v2 addendum): `app/claude_code_client.py`, `app/mcp_server.py`, `app/tools/session_store.py`, `mcp-config.json`, `Dockerfile`.

- **Subprocess invocation is not shell-injectable**: `subprocess.run(command, ...)` is called with `command` as a list (no `shell=True`), and the only user-influenced value in it is `user_text` passed as a single argv element to `-p` — it's never interpolated into a shell string, so it can't break out of its argument position.
- **Tool surface is narrower than before, not wider**: `--allowedTools` is an explicit allowlist of exactly the 5 MCP tools (`mcp__butler__*`); the headless process is given no `Bash`, `Read`, `Write`, or other built-in tool access, so it can't touch the container filesystem beyond what `app/tools/*` itself exposes. This is a stricter boundary than the old design, which only ever offered the same 5 Anthropic tool-use schemas but had no analogous "nothing else exists" enforcement mechanism at the transport level.
- **`app/tools/*` logic is untouched**: `wiki_tools.py`'s slug validation (`UnsafeSlugError`, the High finding from the original review) and `calendar_tools.py`'s create-only constraint are called through unchanged from `app/mcp_server.py` — the MCP wrappers do no argument transformation before delegating, so neither finding is reopened.
- **New secret**: `CLAUDE_CODE_OAUTH_TOKEN` replaces `ANTHROPIC_API_KEY` in `.env` (gitignored, same as before) — no change to the project's secret-handling posture, just a different credential.
- **Error handling**: a non-zero `claude` exit or a response missing `result` raises `ClaudeCodeError`, caught by `main.py`'s existing try/except around `_handle_voice_message` (same pattern already reviewed for `ffmpeg` failures in the v1.1 addendum) — no silent failure mode introduced.

No new findings. **Verdict: PASS** still holds.

## v3 addendum — text and document input

Reviewed the new text/document message paths (`docs/architecture/voice-relay.md`'s v3 addendum): `app/telegram.py`'s new extractors, `app/main.py`'s type-branching, `app/tools/document_tools.py`'s `save_document`.

### High (found and fixed) — unsanitized file extension in `save_document` (`app/tools/document_tools.py`)

`save_document` writes to `docs_dir() / f"{slug}.{ext}"`. `slug` is always passed through `slugify()` (ASCII kebab-case only), but `ext` — taken from `filename.rsplit(".", 1)[1]`, and `filename` is the sender's own Telegram document filename, fully attacker/user-controlled — was only `.lower()`'d before reaching that path construction. A crafted filename (e.g. `evil.txt/../../root/.ssh/authorized_keys`, where the *last* `.` in the string lands inside a `..` segment) could smuggle a `/` or `..` into `ext`, escaping `docs_dir()`.

**Fix applied**: `VALID_EXT = re.compile(r"^[a-z0-9]{1,10}$")`, checked right after lowercasing; anything that doesn't match falls back to a safe `bin` extension. Added `test_save_document_rejects_unsafe_extension` (`test_document_tools.py`), parametrized over three traversal-shaped filenames, asserting every file written during the call is a direct child of the docs directory — none escape it.

This is the same class of finding as the original review's wiki-slug path traversal, in a new module that reached the filesystem for the first time in this addendum.

### Security notes

- Auth model unaffected: `verify_webhook_secret` still runs first, unconditionally, before any payload-shape branching (`app/main.py`) — confirmed the type-branching restructure didn't reorder this. The `chat_id` ownership check now runs generically once *some* actionable type is found, rather than being voice-specific — an unhandled type (sticker, edited_message, etc.) still gets `200` without a `chat_id` check, matching the original accepted "nothing to authorize when nothing is processed" reasoning, just generalized to more types than one. (A later fix added photo support — `extract_photo_message`, routed through the same `save_document` path as a document upload — closing a gap where images sent via Telegram's Photo picker were silently dropped.)
- `save_document` never executes `claude` or any subprocess — it's plain file I/O, so it doesn't inherit `claude_code_client.py`'s subprocess-injection considerations at all.
- Text messages reach `claude_code_client.get_reply` exactly as voice transcripts already do (same argv-list subprocess call, same `--allowedTools` allowlist) — no new surface, just a second caller of an already-reviewed function.

No other new findings. **Verdict: PASS** still holds.

## v4 addendum — document content reading (`enrich_document`, `categorize_document`)

Reviewed the v1.5 change (`docs/architecture/voice-relay.md`'s v4 addendum): `app/claude_code_client.py`'s `enrich_document`, `app/tools/document_tools.py`'s `categorize_document`, `app/mcp_server.py`'s new tool registration, `app/main.py`'s updated `_handle_document_message`.

This is a genuine, deliberate widening of the attack surface — the first time the headless process gets any filesystem `Read` access — so it got the most scrutiny of anything in this epic since the original two High findings.

- **Scoping verified**: `enrich_document` passes `--add-dir <file_path.parent>` (the docs directory only) and `--allowedTools "Read,mcp__butler__categorize_document,mcp__butler__save_memory"` — confirmed neither the app source directory (`/app`) nor the wiki directory (`/data/wiki`) is ever passed to `--add-dir` for this call, and the conversational path's `ALLOWED_TOOLS`/`get_reply` is completely untouched (still zero `Read`, still the original 5 MCP tools). `test_enrich_document_scopes_read_to_the_files_own_directory` asserts the exact `--add-dir` value and that `Read`/`categorize_document` are present while `create_calendar_event` is absent from the allowlist.
- **No secret file to leak even in the worst case**: confirmed by inspecting `docker-compose.yml` directly — `.env` appears only under `env_file:` for both services, never under `volumes:`, so it's never mounted into the container filesystem; Compose injects it purely as process environment variables at container start. `Read` has no file-based mechanism to reach process environment variables. This means even a hypothetical scoping bug in `--add-dir` couldn't leak `CLAUDE_CODE_OAUTH_TOKEN`/`TELEGRAM_BOT_TOKEN`/etc. via this path — belt-and-suspenders on top of the `--add-dir` scoping itself, not a substitute for it.
- **`categorize_document` is safe to expose as an MCP tool where `save_document` wasn't**: it takes a `slug` (an existing filename reference) and `title`/`category` strings, never raw file bytes — the byte-transfer constraint that forced `save_document` to bypass `claude` entirely doesn't apply here.
- **`categorize_document`'s rename logic reuses `save_document`'s already-reviewed disambiguation rule** (numeric qualifier on collision with a *different* document), with one correctness addition: renaming to a slug that happens to coincide with the document's own current slug is correctly treated as "no collision," not an infinite/off-by-one disambiguation loop — covered by `test_categorize_document_updates_in_place_when_title_unchanged`.
- **Indirect prompt injection, residual/accepted**: an uploaded document's content reaches the model as untrusted input, same category of risk as a voice transcript or typed message already carries. A crafted document could attempt to make the model call `save_memory`/`categorize_document` with attacker-chosen content. Bounded by the tight `--allowedTools` for this pass (no calendar/reminders/find_document, and critically no `Bash`) — worst case is a spurious or misleading memory/document label, not filesystem or credential exposure. Not a new class of risk introduced by this addendum, just a new instance of one the conversational path already accepted.
- **Frontmatter field values (`title`, `category`) aren't newline-sanitized before being written as `key: value` lines** — same pre-existing pattern as `wiki_tools.py`'s `save_memory` (`title` there has the identical property, already reviewed and accepted in the original pass). An embedded newline could in principle inject an extra frontmatter-looking line into the *same* sidecar file — a data-integrity nuisance (a malformed/confusing sidecar), not a path-traversal or cross-file issue, since `parse_page` never treats content from one file as a path into another. Consistent with, not worse than, the existing accepted risk profile; not treated as a new finding.

No High or Medium findings. **Verdict: PASS** still holds.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `technical-writer` (`/technical-writer`).

# Persistence Design: Voice Relay

Two very different persistence concerns: a genuinely new, minimal schema for session state, and pure reuse (zero changes) of the existing wiki/document file conventions.

## Session store (new)

SQLite, `backend/voice-relay/data/sessions.db` (gitignored — this is runtime scratch data, not source).

```sql
CREATE TABLE sessions (
    chat_id TEXT PRIMARY KEY,
    history_json TEXT NOT NULL,   -- JSON array of {role, text, timestamp}, capped at ~8 entries
    updated_at TEXT NOT NULL      -- ISO 8601, used for TTL expiry (30 min)
);
```

- One row per `chat_id`. `history_json` is a bounded ring buffer, trimmed to the last ~8 turns on write — never grows unbounded.
- On read, if `updated_at` is older than the TTL, treat as if the row didn't exist (fresh session) rather than deleting it outright — simplest correct behavior, avoids a separate cleanup job for v1.
- Chosen over an in-memory dict specifically so a process restart during local dev doesn't wipe an in-progress test conversation, without introducing a new persistent-data-loss requirement (losing this on restart is still explicitly an accepted limitation — see `specs/stories/voice-relay/voice-conversation.md`'s edge cases).

## Wiki / document data (reused, zero format changes)

The relay reads/writes `backend/memory-module/wiki/*.md` and `backend/document-module/files/*.md` using **exactly** the conventions already defined in `docs/db/memory-module.md` and `docs/db/document-module.md` — same frontmatter fields, same `[[wiki-link]]` syntax, same merge-vs-create rules for `save_memory`, same reserved-page rules for `append_reminder` (`reminders.md`, accumulates, never replaced — see `docs/domain/memory-module.md`'s v1.4 note). Nothing here introduces a second format; a page written by the relay must be indistinguishable from one written by `remember`.

**Location resolution**: `WIKI_REPO_PATH`/`DOCS_REPO_PATH` (env vars) point directly at the existing local directories when running on the same machine as the desktop Claude Code session (no redundant clone, no second source of truth during Phase 1 testing). `WIKI_REPO_URL`/`DOCS_REPO_URL` are configured so the same code clones fresh via `WIKI_GIT_TOKEN` (a fine-grained PAT scoped only to `butler-memory`+`butler-documents`) wherever those local directories don't already exist — e.g. the Phase 2 VPS.

**Two-writer concurrency**: since both the relay and a desktop Claude Code session can write to the same files, `app/wiki_sync.py` runs `git pull --rebase` before any read or write, and on a push conflict retries once, then logs (not fails) — the write itself already landed locally either way.

## v2 addendum — session_id replaces transcript history

`docs/architecture/voice-relay.md`'s v2 addendum (headless Claude Code, no pay-per-token billing) replaces this table's `history_json` column with the Claude Code session id it now resumes via `--resume` instead of manually replaying a transcript:

```sql
CREATE TABLE sessions (
    chat_id TEXT PRIMARY KEY,
    claude_session_id TEXT NOT NULL,  -- id returned by `claude -p --output-format json`, passed to --resume on the next turn
    updated_at TEXT NOT NULL          -- ISO 8601, used for TTL expiry (30 min, unchanged)
);
```

Same TTL-expiry behavior as before (stale row treated as no-session, not deleted). No change to the wiki/document persistence section below.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `frontend-developer` — expected to confirm no dedicated UI (Telegram itself is the interface), then `backend-developer` for implementation.

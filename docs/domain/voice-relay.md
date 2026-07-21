# Domain Model: Voice Relay

## Entities

### Session (new — distinct from Memory's `WikiPage`)

Short-term, per-conversation state — not a memory, not persisted to the wiki. Exists only to let follow-up turns ("actually make it 2pm") resolve correctly.

| Field | Type | Notes |
|---|---|---|
| `chat_id` | string | Telegram chat identifier. Primary key. |
| `claude_session_id` | string | Headless Claude Code's own session id, passed to `--resume` on the next turn (v2 addendum, `docs/architecture/voice-relay.md`) — supersedes the earlier manually-replayed `history` field. |
| `updated_at` | datetime | Set on every turn; used for TTL expiry. |

**Invariants**:
- `chat_id` is unique — one session per conversation.
- A session with `updated_at` older than the TTL (30 minutes) is treated as expired: a new turn starts a fresh session rather than resuming stale context.
- Session loss on process restart is an accepted limitation for v1 — `Session` is not git-backed, unlike `WikiPage`.

### Notification (new, v1.6 addendum — distinct from `Session`)

A proposed-then-maybe-sent proactive message. Not conversational state (unlike `Session`) and not persisted knowledge (unlike `WikiPage`) — it's an audit/dedup record for the one path that initiates contact rather than reacting to a message.

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Autoincrement primary key — not `dedup_key`, since the same `dedup_key` can legitimately produce multiple rows over time (re-proposed after a cooldown). |
| `dedup_key` | string | Stable across runs for the same underlying thing — a Calendar event's own id for an appointment, a semantic slug (e.g. `checkup-due-2026`) for a fuzzy/recurring item. |
| `message` | string | Ready to send as-is; the model wrote it, not a template. |
| `status` | enum | `proposed` → `sent` \| `deferred` \| `suppressed`. Set by `app/claude_code_client.py`'s `propose_notification` tool (always `proposed`) and then by `app/proactive.py`'s gate (never by the model). |
| `proposed_at` | datetime | Set at creation. |
| `sent_at` | datetime, nullable | Set only when `status` becomes `sent`. |

**Invariants**:
- A `Notification` is created only by the `propose_notification` MCP tool, called only from the daily proactive scan — nothing in the reactive (voice/text/document) path ever writes one.
- Creating a `Notification` never sends anything by itself — `status='proposed'` rows are inert until `app/proactive.py`'s gate processes them.
- A `dedup_key` with a `sent` row within the cooldown window suppresses a new proposal for the same key — the same underlying appointment/pattern is never re-notified while still within cooldown, but can resurface after it if still genuinely true.

### WikiPage (reused, not redefined)

The relay reads and writes the *same* `WikiPage` entity Memory already defines (`docs/domain/memory-module.md`) — same fields, same invariants, same file format (`docs/db/memory-module.md`). No new fields, no new file format. The relay's `wiki_tools.py` is a second implementation reading/writing the same files `remember`/`recall` do, not a fork of the format.

## Relationships

`Session` has no relationship to `WikiPage` in the domain model — a session is purely transient conversational context; anything worth keeping crosses over into a `WikiPage` write (`save_memory`/`append_reminder`), at which point it's governed entirely by Memory's existing rules (merge-vs-create, tag inference, etc.), not by anything session-specific. `Notification` likewise has no relationship to `WikiPage` or `Session` — it's an audit/dedup log for the proactive scan, not a record of anything the user asked for.

## Non-entities considered and excluded

- **"Conversation history" as a persisted entity**: deliberately transient (`Session`, TTL-based, in-memory/SQLite scratch data) — nothing here is meant to survive as a permanent record. If something from a conversation is worth remembering, it becomes a `WikiPage` write instead.
- **"Calendar event" as a domain entity in this repo**: not modeled here — the relay calls Google Calendar's API directly and doesn't keep its own copy of event data; Google Calendar is the system of record, same as it already is for `remember`'s v1.5 Calendar-event-creation and `sync-calendar`. `list_upcoming_events` (v1.6) reads it fresh each scan for the same reason — no local cache/copy.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

This epic's domain model is complete through v1.6 (`Session`, `Notification`, reused `WikiPage`) — no further stage hand-off pending.

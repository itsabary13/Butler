# Domain Model: Voice Relay

## Entities

### Session (new — distinct from Memory's `WikiPage`)

Short-term, per-conversation state — not a memory, not persisted to the wiki. Exists only to let follow-up turns ("actually make it 2pm") resolve correctly.

| Field | Type | Notes |
|---|---|---|
| `chat_id` | string | Telegram chat identifier. Primary key. |
| `history` | list of turns (role, text, timestamp) | Recent conversation turns, bounded (last ~8). |
| `updated_at` | datetime | Set on every turn; used for TTL expiry. |

**Invariants**:
- `chat_id` is unique — one session per conversation.
- A session with `updated_at` older than the TTL (30 minutes) is treated as expired: a new turn starts a fresh session rather than resuming stale context.
- Session loss on process restart is an accepted limitation for v1 — `Session` is not git-backed, unlike `WikiPage`.

### WikiPage (reused, not redefined)

The relay reads and writes the *same* `WikiPage` entity Memory already defines (`docs/domain/memory-module.md`) — same fields, same invariants, same file format (`docs/db/memory-module.md`). No new fields, no new file format. The relay's `wiki_tools.py` is a second implementation reading/writing the same files `remember`/`recall` do, not a fork of the format.

## Relationships

`Session` has no relationship to `WikiPage` in the domain model — a session is purely transient conversational context; anything worth keeping crosses over into a `WikiPage` write (`save_memory`/`append_reminder`), at which point it's governed entirely by Memory's existing rules (merge-vs-create, tag inference, etc.), not by anything session-specific.

## Non-entities considered and excluded

- **"Conversation history" as a persisted entity**: deliberately transient (`Session`, TTL-based, in-memory/SQLite scratch data) — nothing here is meant to survive as a permanent record. If something from a conversation is worth remembering, it becomes a `WikiPage` write instead.
- **"Calendar event" as a domain entity in this repo**: not modeled here — the relay calls Google Calendar's API directly and doesn't keep its own copy of event data; Google Calendar is the system of record, same as it already is for `remember`'s v1.5 Calendar-event-creation and `sync-calendar`.

## Lifecycle Status

See `specs/epics/voice-relay.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `api-designer` — this epic has a real API surface (the Telegram webhook + health endpoint), unlike Memory/Document.

# Domain Model: Memory Module

## Entities

### WikiPage

The single persisted entity for v1. Per `docs/architecture/memory-module.md`, a "memory" isn't its own standalone record — it's content held in (or merged into) a WikiPage.

| Field | Type | Notes |
|---|---|---|
| `slug` | string | Unique identifier and filename (kebab-case of the page's topic). Primary key. |
| `title` | string | Human-readable topic/concept name. |
| `content` | text (Markdown) | The actual remembered information. Must be non-empty. |
| `links` | list of `slug` | Outgoing `[[wiki-link]]` references to related pages (see Relationships). |
| `created_at` | datetime | Set once, when the page is first created. |
| `updated_at` | datetime | Set whenever the page is merged/extended with new information. |
| `tag` | enum: `private`, `work`, or absent | Added in v1.1 (`tag-memory.md`). Optional — most pages will have no value. Set once, at creation, from the save-time signal; not editable in this increment (retagging is out of scope). |

**Invariants**:
- `slug` is unique across the wiki — no two pages share a filename.
- `content` must be non-empty (a page must hold some remembered information — matches the save-memory story's edge case that a save must never silently no-op).
- Every entry in `links` must reference a `slug` that exists as an actual WikiPage — no dangling links.
- `created_at` <= `updated_at`.
- `tag`, when present, must be exactly `private` or `work` — no other values, no multiple tags on one page (v1.1).

## Relationships

`WikiPage` has a self-referential many-to-many relationship, "relates to," via `links`:

```
erDiagram
  WIKI_PAGE {
    string slug PK
    string title
    text content
    datetime created_at
    datetime updated_at
    string tag "optional: private | work"
  }
  WIKI_PAGE ||--o{ WIKI_PAGE : "relates to (wiki-link)"
```

A page can link to zero or more other pages, and be linked from zero or more other pages. Storage records a link as a directed reference (written by whichever page's save/merge added it), but retrieval traversal (per the retrieve-memory story's requirement to follow links from an initial match) should treat the graph as effectively undirected — a related page should be discoverable regardless of which page recorded the link first. (Exact traversal mechanics are `backend-developer`'s to implement; this is a domain-level note, not an algorithm spec.)

## Note on the calendar sync page (v1.3, exception to the merge rule)

`sync-calendar` (`.claude/skills/sync-calendar/SKILL.md`) maintains exactly one reserved `WikiPage` — slug `upcoming-events` — whose `content` is **replaced wholesale on every sync**, not merged/appended like every other page. This is a deliberate, narrow exception: a rolling snapshot of upcoming events has no meaning to preserve once superseded by a fresher sync, unlike a fact about a person or topic. It does **not** reopen the deferred "Update memory" capability — that would mean editing the content of *arbitrary* pages after the fact; this is a single, reserved page whose entire reason for existing is to be replaced. `created_at` is set once (first sync); `updated_at` changes on every subsequent sync, per the existing invariant.

## Note on the reminders page (v1.4, second exception to the merge rule)

A second reserved `WikiPage` — slug `reminders` — holds structured, date-triggered items rather than freeform prose, and is edited as a **structured list**, not merged as prose the way ordinary pages are: `remember` appends/updates one line per reminder (`- <date-or-recurrence-rule>: <description>`) rather than appending a new paragraph. Unlike `upcoming-events` (fully replaced each sync), `reminders` accumulates — entries persist until explicitly removed, since a reminder ("every 10th, deposit the rental check") doesn't go stale the way a calendar snapshot does. This still doesn't reopen "Update memory": it's edits to one reserved page's structured list, not arbitrary editing of arbitrary pages.

## Note on reminders also becoming Calendar events (v1.5)

Not a new domain entity — when `remember` writes a line to `reminders.md`, it also creates a **recurring Google Calendar event** (via `create_event`'s `recurrenceData`/RRULE support) with the same date/recurrence rule, on the user's primary calendar. `reminders.md` stays the durable, full-detail private record (used by `recall`); the Calendar event is what lets the daily proactive-digest routine (`docs/workflow.md`) pick up new reminders automatically, since Calendar is a native routine connector — no private-repo or secret access needed, and nothing about the reminder is ever written anywhere public. (An earlier design considered a sanitized public index instead; rejected in favor of this since it needed no public exposure at all.)

## Note on deferred capabilities

The epic still defers "Link related memories" as a standalone user-facing capability (see `specs/epics/memory-module.md`'s out-of-scope list) — the `links` relationship above already exists in v1 as internal domain plumbing (it's what lets the save flow avoid creating duplicate pages, FR-2 of `save-memory.md`, and lets retrieval follow connected context, FR-2 of `retrieve-memory.md`). A future epic implementing "Link related memories" as an explicit feature should **extend this existing relationship** rather than introduce a second, competing link mechanism.

"Tag memories" (v1.1) is now in scope as the single `tag` field above — a plain enum, not a list, since v1.1 only supports one tag per page and no retagging. If a future increment wants free-form multi-tag support, that would replace this field rather than sit alongside it (avoid maintaining two competing classification mechanisms).

## Non-entities considered and excluded

- **"Wiki" as an entity**: the wiki is just the directory/collection of `WikiPage`s (its physical location is an architecture/database-design concern, not a domain entity with its own fields).
- **"Query"**: a query is a transient input to the retrieve flow, not a persisted domain object.

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

`docs/architecture/memory-module.md` marks API Design as Not Applicable (no server/network boundary) — per the workflow's hand-off rule, skip `api-designer` and go straight to `database-designer` (`/database-designer`), which will define the wiki's page-naming/slug convention and finalize the storage path.

# Epic: Memory Module

**Status: Shipped** (v1 + v1.1 + v1.2 (auto-push backup) + v1.3 (calendar sync) + v1.4 (reminders page) — see `docs/features/memory-module.md`)

## Idea

Foundational module for Jarvis: lets the AI remember information across conversations and retrieve it when relevant. First epic in the MVP roadmap (Phase 1) and the foundation for all future AI interactions.

## Full long-term capability set (from the master plan — NOT all in v1 scope)

- Create memory
- Update memory
- Delete memory
- Search memories
- Tag memories
- Link related memories
- AI retrieval

## v1 scope (fixed — do not re-decide; `requirements-analyst` works within this)

IN SCOPE:
- Create (save) a memory
- Retrieve memories via AI-assisted search

OUT OF SCOPE for v1 (explicitly deferred, revisit as later stories/epic increments):
- Update memory
- Delete memory
- Tag memories
- Link related memories

"Search" here means AI-assisted retrieval, not a separate keyword-search feature — see the data-layer constraint below.

## v1.1 scope — Tag memories (added after v1 shipped)

IN SCOPE:
- Optionally classify a memory as **Private** or **Work** at save time. Tagging is **optional** — a memory can also stay untagged.
- **New saves only.** Retagging or editing the tag of an already-saved memory is OUT OF SCOPE for this increment (that would require the still-deferred "Update memory" capability) — memories saved before this increment (e.g. `user-name.md`, `kia-license-plate.md`) remain untagged.
- `recall` can filter to only Private or only Work memories when the query implies that scope.

Still OUT OF SCOPE: Update memory, Delete memory, Link related memories (as a standalone feature).

## v1.2 — Automatic backup push (fast-path increment)

`remember` now commits and pushes the wiki's private backup repo (`backend/memory-module/README.md`) after every save by default, opt-out per save via "no push" in that save's message. No new component — reuses the existing backup repo set up when the durability gap was raised. See `docs/architecture/memory-module.md`'s Durability note and `.claude/skills/remember/SKILL.md` step 7.

## v1.3 — Calendar sync (fast-path increment, one exception noted)

A new skill, `sync-calendar`, pulls upcoming events from the user's primary Google Calendar (`itsabary@gmail.com` only, upcoming events only, default 7-day window) into one reserved wiki page (`upcoming-events.md`). Explicitly does **not** send reminders/notifications — no background process exists in this architecture, so that would need genuinely different infrastructure and is deliberately left as a separate, not-yet-built feature. Repeatable on demand ("sync my calendar" or asking what's coming up).

One documented exception to Memory's core rule: this reserved page is **replaced wholesale on every sync**, not merged/appended — see `docs/domain/memory-module.md` and `docs/db/memory-module.md` for why this doesn't reopen the deferred "Update memory" capability. Reuses the existing auto-push backup behavior from v1.2.

## v1.4 — Reminders page (fast-path increment, second reserved-page exception)

A second reserved wiki page, `reminders.md`, holds structured date/recurrence-triggered action items (`- <date-or-recurrence-rule>: <description>`), separate from ordinary freeform memory pages. `remember` now also writes to this page (in addition to a normal topic page, when relevant) whenever new information both has a date/recurrence and describes an action needed — conservatively triggered, since most saved facts aren't reminders. Unlike `upcoming-events.md` (replaced wholesale each sync), `reminders.md` **accumulates** lines over time, since a reminder doesn't go stale the way a calendar snapshot does.

Built as the foundation for a proactive-digest feature (see `docs/workflow.md`'s mobile-access notes). The originally-planned delivery mechanism (a durable `RemoteTrigger` routine reading this page via a scoped GitHub token, notifying via Telegram) hit two real platform constraints during setup: routines currently cannot attach private GitHub repos at all ([documented bug](https://github.com/anthropics/claude-code/issues/64130)), and the routine-creation UI has no environment-variable/secret-storage mechanism, so no token (Telegram or GitHub) can be safely supplied to a routine at all in the current build.

**Actual v1.4 delivery**: a `claude.ai/code/routines` scheduled routine using only native, no-token features — the built-in **Google Calendar connector** (for today's events) and the routine's built-in **push notification on completion** (for delivery), which itself turned out to require Remote Control paired to this machine (confirmed by testing) — undocumented, but real. Initially the routine's instructions hardcoded the one existing reminder as text, since the routine can't read `reminders.md` directly.

## v1.5 — Reminders also become Calendar events (removes the hardcoding)

A cleaner fix for "the routine can't read `reminders.md`": `remember` now also creates a **recurring Google Calendar event** (matching RRULE) for every reminder it records, on the user's primary calendar. The routine's existing Calendar check picks these up automatically — no hardcoded reminder text in the routine, no public repo exposure (an intermediate design, a sanitized public index mirroring `reminders.md`, was considered and explicitly user-confirmed, but was blocked twice by a safety mechanism regardless of confirmation and abandoned in favor of this approach, which needs no public writes at all). `reminders.md` remains the durable private record for `recall`; the Calendar event is purely what the routine reads.

## Fixed constraints for v1

- **Data layer: a wiki, not a database.** Memory is stored as a small set of interlinked Markdown pages organized by topic/concept ("Karpathy wiki-memory" pattern) — not a per-entry dated log, not a database, not a vector index. Claude itself creates and edits pages, cross-referencing related pages with `[[wiki-links]]`.
- **No server process.** Everything runs locally through Claude Code; there is no backend service to deploy or call over a network.
- **Retrieval is AI-assisted, not indexed.** At query time, Claude browses the wiki — reading relevant pages and following links — and reasons about relevance. There is no keyword index, embedding store, or vector database for v1.

These constraints bind `architect`, `api-designer`, and `database-designer`: API design and conventional database design are expected to be **Not Applicable** for v1 — each should document why, rather than inventing a server or schema. `database-designer` instead documents the wiki's page-naming and linking conventions (see `docs/db/README.md`).

## Lifecycle Status

- [x] Epic / User Stories / Functional Requirements — requirements-analyst — `specs/stories/memory-module/` (v1.1: adds `tag-memory.md`)
- [x] Architecture — architect — `docs/architecture/memory-module.md`
- [x] Domain Model — domain-designer — `docs/domain/memory-module.md` (v1.1: adds optional `tag` field; v1.4: adds `reminders.md` exception note)
- [x] API Design (N/A for v1 — no server/network boundary, see docs/architecture/memory-module.md) — api-designer — `docs/api/memory-module.md`
- [x] Database Design (wiki page structure, not a database) — database-designer — `docs/db/memory-module.md` (v1.1: adds optional `tag` frontmatter field; v1.4: adds reminders page format)
- [x] UI (N/A — no dedicated UI, see docs/ui/memory-module.md) — frontend-developer — `docs/ui/memory-module.md`
- [x] Implementation (backend) — backend-developer — `.claude/skills/remember/`, `.claude/skills/recall/`, `backend/memory-module/` (v1.1: tag inference in `remember`, tag filtering in `recall`; v1.3: new `sync-calendar` skill; v1.4: reminder detection in `remember`)
- [x] Implementation (frontend) (N/A — no UI to implement) — frontend-developer — `frontend/memory-module/` (no subfolder)
- [x] Tests — test-engineer — `docs/tests/memory-module.md` (v1.1: 9/9 tests, incl. tag validation + filtered-recall smoke test; v1.4: reminders detection smoke test)
- [x] Review — reviewer — `docs/reviews/memory-module.md` (PASS; v1.1 tag addendum also PASS, no new high-severity findings)
- [x] Documentation — technical-writer — `docs/features/memory-module.md`

## MVP Roadmap Context

Phase 1 (Authentication, Memory, Notes, Tasks, Search) — Memory is the first epic.

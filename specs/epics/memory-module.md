# Epic: Memory Module

**Status: Shipped** (v1 + v1.1 + v1.2 (auto-push backup) — see `docs/features/memory-module.md`)

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

## Fixed constraints for v1

- **Data layer: a wiki, not a database.** Memory is stored as a small set of interlinked Markdown pages organized by topic/concept ("Karpathy wiki-memory" pattern) — not a per-entry dated log, not a database, not a vector index. Claude itself creates and edits pages, cross-referencing related pages with `[[wiki-links]]`.
- **No server process.** Everything runs locally through Claude Code; there is no backend service to deploy or call over a network.
- **Retrieval is AI-assisted, not indexed.** At query time, Claude browses the wiki — reading relevant pages and following links — and reasons about relevance. There is no keyword index, embedding store, or vector database for v1.

These constraints bind `architect`, `api-designer`, and `database-designer`: API design and conventional database design are expected to be **Not Applicable** for v1 — each should document why, rather than inventing a server or schema. `database-designer` instead documents the wiki's page-naming and linking conventions (see `docs/db/README.md`).

## Lifecycle Status

- [x] Epic / User Stories / Functional Requirements — requirements-analyst — `specs/stories/memory-module/` (v1.1: adds `tag-memory.md`)
- [x] Architecture — architect — `docs/architecture/memory-module.md`
- [x] Domain Model — domain-designer — `docs/domain/memory-module.md` (v1.1: adds optional `tag` field)
- [x] API Design (N/A for v1 — no server/network boundary, see docs/architecture/memory-module.md) — api-designer — `docs/api/memory-module.md`
- [x] Database Design (wiki page structure, not a database) — database-designer — `docs/db/memory-module.md` (v1.1: adds optional `tag` frontmatter field)
- [x] UI (N/A — no dedicated UI, see docs/ui/memory-module.md) — frontend-developer — `docs/ui/memory-module.md`
- [x] Implementation (backend) — backend-developer — `.claude/skills/remember/`, `.claude/skills/recall/`, `backend/memory-module/` (v1.1: tag inference in `remember`, tag filtering in `recall`)
- [x] Implementation (frontend) (N/A — no UI to implement) — frontend-developer — `frontend/memory-module/` (no subfolder)
- [x] Tests — test-engineer — `docs/tests/memory-module.md` (v1.1: 9/9 tests, incl. tag validation + filtered-recall smoke test)
- [x] Review — reviewer — `docs/reviews/memory-module.md` (PASS; v1.1 tag addendum also PASS, no new high-severity findings)
- [x] Documentation — technical-writer — `docs/features/memory-module.md`

## MVP Roadmap Context

Phase 1 (Authentication, Memory, Notes, Tasks, Search) — Memory is the first epic.

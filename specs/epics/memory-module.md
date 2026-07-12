# Epic: Memory Module

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

## Fixed constraints for v1

- **Data layer: a wiki, not a database.** Memory is stored as a small set of interlinked Markdown pages organized by topic/concept ("Karpathy wiki-memory" pattern) — not a per-entry dated log, not a database, not a vector index. Claude itself creates and edits pages, cross-referencing related pages with `[[wiki-links]]`.
- **No server process.** Everything runs locally through Claude Code; there is no backend service to deploy or call over a network.
- **Retrieval is AI-assisted, not indexed.** At query time, Claude browses the wiki — reading relevant pages and following links — and reasons about relevance. There is no keyword index, embedding store, or vector database for v1.

These constraints bind `architect`, `api-designer`, and `database-designer`: API design and conventional database design are expected to be **Not Applicable** for v1 — each should document why, rather than inventing a server or schema. `database-designer` instead documents the wiki's page-naming and linking conventions (see `docs/db/README.md`).

## Lifecycle Status

- [x] Epic / User Stories / Functional Requirements — requirements-analyst — `specs/stories/memory-module/`
- [x] Architecture — architect — `docs/architecture/memory-module.md`
- [x] Domain Model — domain-designer — `docs/domain/memory-module.md`
- [x] API Design (N/A for v1 — no server/network boundary, see docs/architecture/memory-module.md) — api-designer — `docs/api/memory-module.md`
- [x] Database Design (wiki page structure, not a database) — database-designer — `docs/db/memory-module.md`
- [ ] UI — frontend-developer — `docs/ui/memory-module.md`
- [ ] Implementation (backend) — backend-developer — `backend/memory-module/`
- [ ] Implementation (frontend) — frontend-developer — `frontend/memory-module/`
- [ ] Tests — test-engineer — `docs/tests/memory-module.md`
- [ ] Review — reviewer — `docs/reviews/memory-module.md`
- [ ] Documentation — technical-writer — `docs/features/memory-module.md`

## MVP Roadmap Context

Phase 1 (Authentication, Memory, Notes, Tasks, Search) — Memory is the first epic.

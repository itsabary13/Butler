# Epic: Document Module

**Status: Shipped** (v1 + v1.1 (Google Drive source) + v1.2 (backup repo) — see `docs/features/document-module.md`)

## Idea

Lets the user store and later retrieve actual files (PDFs, Word documents, images, etc.) through Jarvis — distinct from the Memory module, which only stores text facts. Per the master plan's MVP roadmap, "Documents" is its own Phase 2 capability, separate from Memory (Phase 1).

## v1 scope (fixed — do not re-decide; `requirements-analyst` works within this)

IN SCOPE:
- Add a document: store a real file (its bytes, unmodified) plus a small amount of metadata (title/topic, original filename, when it was added).
- Retrieve a document: find and open a previously-added document when asked about it, using the same AI-assisted-reasoning retrieval style as Memory's `recall` (no keyword index).

OUT OF SCOPE for v1 (explicitly deferred):
- Deleting or replacing/updating an already-added document.
- Folder/category organization beyond one flat store.
- Private/Work tagging (Memory has this; Documents doesn't yet — can be added later the same way, once there's real usage to justify it).
- Full-text search/indexing/OCR inside document contents — retrieval works by Claude reading metadata (and the file itself, for text-readable formats) at query time, not a pre-built index.
- Cross-linking a document to a specific Memory wiki page — the two modules stay independent for v1.

## v1.1 — Add from Google Drive (fast-path increment)

`add-document` can now also source a file from the user's Google Drive, not just a local path — same storage/metadata model, just a second acquisition step (download via Drive's API, decode, write bytes directly — never round-tripped through the model's text tools, same rule as the local-copy path). Google-native files (Docs/Sheets/Slides) are exported as PDF by default. No new component, no new entity.

## v1.2 — Backup repo (fast-path increment)

`backend/document-module/files/` is now its own independent git repo, backed up to a separate private GitHub repo (`backend/document-module/README.md` has the URL), same pattern as Memory's `butler-memory` backup. Closes the durability gap flagged when this epic first shipped. Unlike Memory's `remember`, `add-document` doesn't auto-push after every add yet — pushes are manual for now.

## Fixed constraints for v1

- **No server process** — same constraint as Memory. Everything happens locally through Claude Code reading/writing files directly.
- **Storage mirrors Memory's pattern for consistency**: each document gets a small Markdown metadata sidecar (frontmatter + freeform notes) alongside the original file, rather than a database. `database-designer` finalizes the exact layout.
- **Independent from the Memory module** — a separate store, separate skills, no shared code, even though both are "things Jarvis remembers about you." (See `docs/architecture/document-module.md` for why they aren't merged.)

## Lifecycle Status

- [x] Epic / User Stories / Functional Requirements — requirements-analyst — `specs/stories/document-module/`
- [x] Architecture — architect — `docs/architecture/document-module.md`
- [x] Domain Model — domain-designer — `docs/domain/document-module.md`
- [x] API Design (N/A — no server, see docs/architecture/document-module.md) — api-designer — `docs/api/document-module.md`
- [x] Database Design (file + metadata layout, not a database) — database-designer — `docs/db/document-module.md`
- [x] UI (N/A — no dedicated UI, see docs/ui/document-module.md) — frontend-developer — `docs/ui/document-module.md`
- [x] Implementation (backend) — backend-developer — `.claude/skills/add-document/`, `.claude/skills/find-document/`, `backend/document-module/` (v1.1: Google Drive as a second source)
- [x] Implementation (frontend) (N/A — no UI to implement) — frontend-developer — `frontend/document-module/` (no subfolder)
- [x] Tests — test-engineer — `docs/tests/document-module.md` (5/5 tests, incl. add+retrieve smoke test)
- [x] Review — reviewer — `docs/reviews/document-module.md` (PASS; 1 high finding fixed during review, 1 medium follow-up recommendation)
- [x] Documentation — technical-writer — `docs/features/document-module.md`

## MVP Roadmap Context

Phase 2 (Projects, Knowledge Base, Documents) per the master plan — built ahead of schedule at the user's request, same as Memory's tagging/backup increments were.

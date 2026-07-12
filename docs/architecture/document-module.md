# Architecture: Document Module

## Why a separate module from Memory

Memory (`docs/architecture/memory-module.md`) stores short text facts as a wiki of Markdown pages meant to be merged and cross-linked over time. Documents are opaque binary files (PDFs, Word docs, images) — merging two PDFs into "one topic" the way two memories merge into one wiki page doesn't make sense, and a document's content isn't something Claude can (or should) inline into a shared text page. The user confirmed keeping these as two independent epics rather than folding documents into the Memory wiki.

## Module boundaries

1. **Document Writer** — implements the Add story (`specs/stories/document-module/add-document.md`). Sources a file from either a local path or the user's Google Drive (v1.1 addition) — both converge on the same exact-bytes-to-disk write, just a different acquisition step.
2. **Document Retriever** — implements the Retrieve story (`specs/stories/document-module/retrieve-document.md`).
3. **Document Store** — the shared storage both components read/write (see Domain Model / Database Design for its structure).

No shared code with the Memory module — same architectural pattern (Claude Code skills, no server, no database), applied independently.

## Runtime model

Same decision as Memory: no server process. Implemented as two Claude Code product skills:

- **`add-document`** — implements the Document Writer. `disable-model-invocation: false` — Claude invokes it when the user provides a file and asks to save/store it.
- **`find-document`** — implements the Document Retriever. `disable-model-invocation: false` — Claude invokes it when a question implies looking up a previously-added document.

## Components & data flow

```
User provides a file + asks to save it
   |
   v
Claude (Jarvis) -- copies bytes + writes metadata --> [add-document skill] --> Document Store
                                                                                     |
User asks about a document later                                                   |
   |                                                                                v
Claude (Jarvis) -- reads metadata, opens matching file --> [find-document skill] <--+
```

No network boundary. Everything happens in-process, reading/writing local files during a Claude Code session — same as Memory.

Proposed physical location: `backend/document-module/files/` (default-only — `database-designer` owns and can override the final convention).

## Technology / data-layer decision

- Storage: original files stored as-is, plus a Markdown metadata sidecar per file (mirrors Memory's frontmatter pattern for consistency, even though the "content" here is a separate binary rather than the Markdown body itself).
- No database engine, no server, no REST/network boundary.
- No content-indexing/OCR pipeline — retrieval is Claude reasoning over metadata (and reading the file directly for formats it can read, e.g. PDF, plain text) at query time.

## Non-functional constraints

- **Privacy**: same class of concern as Memory — documents can contain personal/sensitive content. `database-designer`/`reviewer` should confirm the store is gitignored from the main repo, same treatment as `backend/memory-module/wiki/`.
- **Durability**: resolved (v1.2) the same way as Memory — `files/` is its own git repo, pushed to a separate private GitHub repo (`backend/document-module/README.md` has the URL). (v1.3: `add-document` now pushes automatically after every add, opt-out per add via "no push," same as `remember`.)
- **Storage size**: unlike Memory's small text pages, real files (PDFs, images) can be large. A private git repo backup (if adopted, per the durability note) may not be the ideal fit for very large or many files long-term — flagging as a known limitation, not solving now, since v1 has no size constraint from the user.
- **Content readability**: Claude can only meaningfully summarize/answer questions about formats it can read directly (e.g. PDF, plain text) — opaque formats are stored and locatable but not searchable by content in v1 (see `retrieve-document.md`'s edge case).

## Downstream stage applicability

- **API Design: Not Applicable.** No server/network boundary — same reasoning as Memory.
- **Database Design: Redirected, not skipped.** `database-designer` defines the file+metadata storage layout (naming convention, sidecar format), not a schema.
- **UI: Expected Not Applicable for v1.** Interaction is conversational — `frontend-developer` should confirm this explicitly rather than build one.

## Lifecycle Status

See `specs/epics/document-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `domain-designer` (`/domain-designer`) — a small domain model (a `Document` entity) is warranted here too.

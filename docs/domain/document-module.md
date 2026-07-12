# Domain Model: Document Module

## Entities

### Document

| Field | Type | Notes |
|---|---|---|
| `slug` | string | Unique identifier and metadata filename (kebab-case of the title, ASCII-only per Memory's established sanitization rule — see `docs/db/memory-module.md`). Primary key. |
| `title` | string | Human-readable topic/name for the document. |
| `original_filename` | string | The filename as provided when added (kept verbatim, unlike `slug`). |
| `file_extension` | string | Derived from `original_filename`; determines the stored file's extension. |
| `added_at` | datetime | Set once, when the document is added. |
| `notes` | text (Markdown), optional | Freeform notes about the document, if any were given at add time. Not the document's own content — just Jarvis's metadata about it. |

**Invariants**:
- `slug` is unique across the store — no two documents share a metadata filename.
- `original_filename` must be non-empty.
- A `Document` always has exactly one corresponding stored file (see Database Design for the pairing convention) — a metadata record with no file, or a file with no metadata record, is invalid.
- `added_at` is immutable once set (no "Update document" capability in v1).

## Relationships

None. Unlike Memory's `WikiPage`, `Document` has no self-referential linking in v1 (cross-document or cross-Memory linking is explicitly out of scope — see `specs/epics/document-module.md`).

## Non-entities considered and excluded

- **Document content itself** isn't modeled as domain data — it's an opaque file. Jarvis reads it directly (for readable formats) rather than extracting/storing structured content from it.
- **Tag** (Private/Work, as Memory has): not included in v1 — deferred, see epic's out-of-scope list. If added later, it should reuse the same enum convention Memory established (`docs/domain/memory-module.md`) rather than inventing a new one.

## Lifecycle Status

See `specs/epics/document-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

`docs/architecture/document-module.md` marks API Design as Not Applicable — skip `api-designer`, go straight to `database-designer` (`/database-designer`).

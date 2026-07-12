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

**Invariants**:
- `slug` is unique across the wiki — no two pages share a filename.
- `content` must be non-empty (a page must hold some remembered information — matches the save-memory story's edge case that a save must never silently no-op).
- Every entry in `links` must reference a `slug` that exists as an actual WikiPage — no dangling links.
- `created_at` <= `updated_at`.

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
  }
  WIKI_PAGE ||--o{ WIKI_PAGE : "relates to (wiki-link)"
```

A page can link to zero or more other pages, and be linked from zero or more other pages. Storage records a link as a directed reference (written by whichever page's save/merge added it), but retrieval traversal (per the retrieve-memory story's requirement to follow links from an initial match) should treat the graph as effectively undirected — a related page should be discoverable regardless of which page recorded the link first. (Exact traversal mechanics are `backend-developer`'s to implement; this is a domain-level note, not an algorithm spec.)

## Note on deferred capabilities

The epic defers "Tag memories" and "Link related memories" as standalone user-facing capabilities (see `specs/epics/memory-module.md`'s out-of-scope list). However, the `links` relationship above already exists in v1 as internal domain plumbing — it's what lets the save flow avoid creating duplicate pages (FR-2 of `save-memory.md`) and lets retrieval follow connected context (FR-2 of `retrieve-memory.md`). When a future epic implements "Link related memories" as an explicit feature, it should **extend this existing relationship** (e.g. adding link metadata/type) rather than introduce a second, competing link mechanism. "Tag memories" would be a genuinely new field (e.g. `tags: list of string`) not modeled here since nothing in the v1 stories requires it.

## Non-entities considered and excluded

- **"Wiki" as an entity**: the wiki is just the directory/collection of `WikiPage`s (its physical location is an architecture/database-design concern, not a domain entity with its own fields).
- **"Query"**: a query is a transient input to the retrieve flow, not a persisted domain object.

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

`docs/architecture/memory-module.md` marks API Design as Not Applicable (no server/network boundary) — per the workflow's hand-off rule, skip `api-designer` and go straight to `database-designer` (`/database-designer`), which will define the wiki's page-naming/slug convention and finalize the storage path.

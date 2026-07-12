# Persistence Design: Memory Module

`docs/architecture/memory-module.md` fixes the data layer as a wiki, not a database — no schema, no migrations. This document defines the wiki's file-level structure, which is the persistence mapping for the `WikiPage` entity (`docs/domain/memory-module.md`).

## Storage location

`backend/memory-module/wiki/` (confirms the architecture doc's proposed default). Created on first write by `backend-developer`'s implementation — it need not exist ahead of time.

## Page/slug naming convention

- One file per `WikiPage`, one page per topic/concept — never one file per raw save (a save either creates a new page or merges into an existing one, per the save-memory story).
- Filename: `<slug>.md`, where `slug` is the kebab-case of the page's `title` (e.g. title "Home Address" -> `home-address.md`).
- Slugs must be unique (domain invariant). On collision with an unrelated page that happens to produce the same slug, disambiguate by appending a short qualifier before slugifying (e.g. "Home Address (Boston)" -> `home-address-boston.md`) rather than a numeric suffix, so the filename stays meaningful on its own.
- Slugs must be restricted to `[a-z0-9-]` (closes the sanitization gap flagged in `docs/reviews/memory-module.md`). If `title` contains characters outside that set (non-Latin script, punctuation, etc.), transliterate to ASCII for the slug/filename only — `title` and `content` keep the original text unchanged. Strip any transliteration result down to `[a-z0-9-]`, collapsing repeated `-`.

## File format

Each page is Markdown with a small YAML frontmatter block plus a freeform content body:

```markdown
---
slug: home-address
title: Home Address
created_at: 2026-07-12T18:30:00Z
updated_at: 2026-07-12T18:30:00Z
tag: private
---

Irene's home address is ...

Related: [[moving-plans]]
```

Frontmatter carries `slug`, `title`, `created_at`, `updated_at`, and (v1.1, optional) `tag` — it deliberately does **not** duplicate the domain model's `links` field as a separate array. Reconciliation with the domain model: `links` is persisted as inline `[[slug]]` references within `content`, not a parallel frontmatter list. Keeping one source of truth avoids the two drifting apart when content is edited but a frontmatter array is forgotten.

**`tag` (v1.1, optional)**: value is exactly `private`, `work`, or the field is omitted entirely (never an empty string, never any other value). Set only at page creation from `remember`'s save-time inference — this increment does not support editing a page's tag afterward, so once written it's not touched again by `remember`'s merge path either.

## `[[wiki-link]]` cross-referencing convention

- A link from page A to page B is written as `[[b-slug]]` somewhere in A's `content`.
- Links are recorded **bidirectionally at write time**: whenever a link is created between two pages, both pages get a `[[...]]` reference to each other. This is what makes the domain model's "retrieval traverses the graph as undirected" note possible without needing a separate backlink index — each file is self-descriptive; reading either page reveals the connection.
- A dangling `[[slug]]` (referencing a file that doesn't exist) violates the domain invariant and must not be produced by the write path — only link to slugs that exist at the time of writing.

## Create vs. merge

- **Create**: no existing page is topically related -> write a new `<slug>.md` with `created_at` = `updated_at` = now.
- **Merge**: an existing related page is found -> append the new information into that page's `content` (as a new paragraph/subsection, not a full rewrite) and set `updated_at` = now. `created_at` is untouched. If the new information also relates to a second existing page, add the bidirectional `[[...]]` link between the merged-into page and that second page.

## Tag-based filtering (v1.1)

Filtering is a read-time concern, not a storage concern: `recall` filters its candidate set by reading each page's `tag` frontmatter field before deciding relevance. No separate index or per-tag directory is introduced — with the wiki's expected size, scanning frontmatter across all pages is cheap enough that a tag index would be premature.

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact. (v1.1 update: added the optional `tag` field.)

## Hand-off

v1 hand-off (historical): `frontend-developer` confirmed no dedicated UI, then `backend-developer` implemented `remember`/`recall`. v1.1 hand-off: back to `backend-developer` (`/backend-developer`) to add tag inference/filtering to the existing skills.

# Persistence Design: Document Module

`docs/architecture/document-module.md` fixes the data layer as files-plus-metadata, not a database. This document defines the storage layout, which is the persistence mapping for the `Document` entity (`docs/domain/document-module.md`).

## Storage location

`backend/document-module/files/` — created on first add; need not exist ahead of time. Gitignored from the main repo, same treatment as `backend/memory-module/wiki/` (see Non-functional constraints in the architecture doc).

## Naming convention

Each `Document` is two files sharing the same `slug`:

- `<slug>.<ext>` — the original file, bytes unchanged, `<ext>` taken from `original_filename`.
- `<slug>.md` — a metadata sidecar (see File format below).

`slug` is the kebab-case of `title`, ASCII-only (reuse Memory's transliteration rule from `docs/db/memory-module.md` — non-Latin titles get transliterated for the filename only, `title` keeps the original text). On slug collision with an unrelated document, disambiguate with a qualifier before slugifying, same as Memory's convention — never silently overwrite an existing document's files.

## File format (metadata sidecar)

```markdown
---
slug: passport-scan
title: Passport Scan
original_filename: passport_scan_2024.pdf
file_extension: pdf
added_at: 2026-07-12T21:00:00Z
---

Scanned copy of the user's passport.
```

`notes` (the domain model's optional freeform field) is the Markdown body, same pattern as Memory's `content`. If there's nothing to say beyond the bare metadata, the body can be a single short line restating the title — never truly empty, so an empty file is never mistaken for a missing/corrupt sidecar.

## Add flow

1. Derive `slug`/`title` (from user-given title, or inferred from the filename if none given).
2. Copy the source file to `<slug>.<ext>` unmodified.
3. Write the `<slug>.md` sidecar with the frontmatter above.
4. On slug collision with an unrelated document: disambiguate the slug (per naming convention) rather than overwrite — matches `add-document.md`'s edge case (same title/topic reused should produce a new, distinct document, not silently replace the old one, since Update/Replace is out of scope).

## Retrieve flow

`find-document` scans `<slug>.md` sidecars (cheap — just frontmatter/title, no need to open every binary), identifies the candidate(s), then opens the actual `<slug>.<ext>` file only for the matching document(s) — mirroring Memory's `recall` pattern of scanning cheaply before reading in full.

## Lifecycle Status

See `specs/epics/document-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `frontend-developer` (`/frontend-developer`) — expected to confirm no dedicated UI, then `backend-developer` (`/backend-developer`) for implementation.

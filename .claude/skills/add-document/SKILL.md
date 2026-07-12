---
name: add-document
description: Stores an actual file (PDF, Word document, image, etc.) the user gives a path to, so it can be found and opened again later. Use whenever the user asks to save, store, or add a document/file to Jarvis, or hands over a file path with an intent to keep it (e.g. "save this PDF", "add this to my documents", "keep a copy of this").
disable-model-invocation: false
---

# Add Document

Implements the Document Writer component of the Document module (`docs/architecture/document-module.md`), against the storage layout defined in `docs/db/document-module.md`. Satisfies the acceptance criteria and functional requirements in `specs/stories/document-module/add-document.md`.

## Storage location

`backend/document-module/files/` — create the directory if it doesn't exist yet.

## Steps

1. **Resolve the source file.** The user must give (or have already given) a path to an existing local file. If the path doesn't exist or can't be read, tell the user clearly and stop — never fabricate a successful add.
2. **Determine the title.** Use a title the user gives explicitly; otherwise infer a reasonable one from the filename (and file content, if quickly inspectable) per `add-document.md`'s acceptance criteria.
3. **Derive the slug.** Kebab-case the title, ASCII-only (transliterate non-Latin titles for the filename only, same rule as Memory — `docs/db/memory-module.md`). On collision with an unrelated existing document's slug, disambiguate with a qualifier rather than overwrite (per `docs/db/document-module.md`).
4. **Copy the file unmodified** to `backend/document-module/files/<slug>.<ext>`, `<ext>` taken from the original filename. **Use a direct filesystem copy command** (e.g. `cp` in Bash, `Copy-Item` in PowerShell) — never read the file's content into the model and write it back out. For binary formats (PDF, images, Word documents — the formats this module exists for), reading through a text-based tool and rewriting the text risks corrupting or truncating the file; a direct OS-level copy preserves the bytes exactly.
5. **Write the metadata sidecar** `backend/document-module/files/<slug>.md` with frontmatter `slug`, `title`, `original_filename`, `file_extension`, `added_at` (now), and a short note in the body (never truly empty — see `docs/db/document-module.md`).
6. **Confirm the outcome to the user** briefly (e.g. "Saved that as a document" / "Got it, stored as X") — same as `remember`, a save must never happen silently, and a failure must be reported, not swallowed.

## Explicitly out of scope

Deleting, replacing, or editing an already-added document; Private/Work tagging; cross-linking to Memory wiki pages — see `specs/epics/document-module.md`'s out-of-scope list. Don't implement them speculatively.

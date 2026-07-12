---
name: add-document
description: Stores an actual file (PDF, Word document, image, etc.) — from a local path or from the user's Google Drive — so it can be found and opened again later. Use whenever the user asks to save, store, or add a document/file to Jarvis, hands over a file path, or asks to import/add something from their Google Drive (e.g. "save this PDF", "add my resume from Drive", "keep a copy of this").
disable-model-invocation: false
---

# Add Document

Implements the Document Writer component of the Document module (`docs/architecture/document-module.md`), against the storage layout defined in `docs/db/document-module.md`. Satisfies the acceptance criteria and functional requirements in `specs/stories/document-module/add-document.md`.

## Storage location

`backend/document-module/files/` — create the directory if it doesn't exist yet.

## Steps

1. **Resolve the source.** Two possible sources:
   - **Local path**: the user gives (or has already given) a path to an existing local file. If it doesn't exist or can't be read, tell the user clearly and stop — never fabricate a successful add.
   - **Google Drive**: the user names or references a Drive file. Use `search_files` to locate it if a specific file ID isn't given, then `get_file_metadata` to confirm the match (name, mimeType) before proceeding. If nothing matches or the match is ambiguous, ask rather than guessing.
2. **Determine the title.** Use a title the user gives explicitly; otherwise infer a reasonable one from the filename/Drive file name (and content, if quickly inspectable) per `add-document.md`'s acceptance criteria.
3. **Derive the slug.** Kebab-case the title, ASCII-only (transliterate non-Latin titles for the filename only, same rule as Memory — `docs/db/memory-module.md`). On collision with an unrelated existing document's slug, disambiguate with a qualifier rather than overwrite (per `docs/db/document-module.md`).
4. **Get the file's exact bytes into `backend/document-module/files/<slug>.<ext>`:**
   - **Local path**: use a direct filesystem copy command (`cp` in Bash, `Copy-Item` in PowerShell) — never read the file's content into the model and write it back out. For binary formats (PDF, images, Word documents), a text-based Read-then-Write round-trip risks corrupting or truncating the file; a direct OS-level copy preserves the bytes exactly.
   - **Google Drive — already a real file** (uploaded PDF, image, Word doc, etc., not a Google-native type): call `download_file_content` with just the `fileId` — it returns the exact original bytes, base64-encoded. Decode the base64 and write the raw bytes directly to disk via a shell command (e.g. PowerShell `[IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($b64))`) — the same "never round-trip through the model's text tools" rule applies to base64-decoded binary as it does to a local copy.
   - **Google Drive — a Google-native file** (Doc/Sheet/Slide, which has no "original bytes" since it isn't a real file until exported): call `download_file_content` with an explicit `exportMimeType` — default to PDF (`application/pdf`) for Docs, Sheets, and Slides alike, since this module is for storing/finding documents, not editing them, and PDF preserves visual fidelity across all three. Then decode and write as above. Only use a different export format if the user asks for one.
5. **Write the metadata sidecar** `backend/document-module/files/<slug>.md` with frontmatter `slug`, `title`, `original_filename` (the Drive file's name, for Drive-sourced documents), `file_extension`, `added_at` (now), and a short note in the body (never truly empty — see `docs/db/document-module.md`). Note the source (local path vs. Drive) in the body for provenance.
6. **Confirm the outcome to the user** briefly (e.g. "Saved that as a document" / "Got it, stored as X") — same as `remember`, a save must never happen silently, and a failure must be reported, not swallowed.

## Explicitly out of scope

Deleting, replacing, or editing an already-added document; Private/Work tagging; cross-linking to Memory wiki pages — see `specs/epics/document-module.md`'s out-of-scope list. Don't implement them speculatively.

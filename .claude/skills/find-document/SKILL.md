---
name: find-document
description: Finds and opens a previously-added document to answer a question or hand it back to the user. Use whenever the user asks about, references, or requests a file they previously stored with Jarvis (e.g. "do you have my passport scan?", "what's in that PDF I gave you about X?", "find the document about Y").
disable-model-invocation: false
---

# Find Document

Implements the Document Retriever component of the Document module (`docs/architecture/document-module.md`), against the storage layout defined in `docs/db/document-module.md`. Satisfies the acceptance criteria and functional requirements in `specs/stories/document-module/retrieve-document.md`.

## Storage location

`backend/document-module/files/`. If this directory doesn't exist or is empty, no documents have been added yet — proceed without error and without fabricating anything.

## Steps

1. **Scan candidates cheaply.** List the `*.md` metadata sidecars under `backend/document-module/files/` and read their frontmatter/title (no need to open the actual binary files yet).
2. **Identify the matching document(s).** Reason about which sidecar(s), if any, relate to the request — by title/topic match or semantic relevance, not strict keyword matching. If several plausibly match, ask a brief clarifying question or list the candidates rather than guessing (per `retrieve-document.md`'s edge case).
3. **Open the matching file** (`<slug>.<ext>`) once identified. For formats Claude can read directly (PDF, plain text, etc.), use its content to answer the user's question or summarize it. For unreadable/opaque formats, still confirm the document exists and where it is, per the edge case in `retrieve-document.md`.
4. **Never fabricate.** If nothing matches, say so rather than inventing a document that was never added.

## Explicitly out of scope

Full-text search/indexing across all documents' contents, and any UI beyond this conversational flow — see `specs/epics/document-module.md`'s out-of-scope list.

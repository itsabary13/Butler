# Story: Retrieve a document

## User story

As a Jarvis user, I want to ask for a document I previously added and have Jarvis find and open it, so that I don't have to remember exactly what it was called or where it's stored.

## Acceptance criteria

- **Given** one or more documents have been added, **when** the user asks about something that relates to a stored document (by topic, not necessarily its exact title), **then** Jarvis identifies the matching document from its metadata and opens/reads it to answer or to confirm it found the right one.
- **Given** no document matches the request, **when** Jarvis searches, **then** it says so rather than fabricating a match.
- **Given** the document store is empty, **when** the user asks for a document, **then** Jarvis handles this gracefully (no error), same as Memory's empty-wiki behavior.
- **Given** the matching document is a format Jarvis can read directly (e.g. PDF, plain text), **when** retrieved, **then** Jarvis can summarize or answer questions about its content, not just confirm it exists.

## Edge cases

- Multiple documents plausibly match a vague request — ask a brief clarifying question or list the candidates rather than guessing silently.
- A document whose format Jarvis can't read the content of (per `add-document.md`'s edge case) — retrieval should still locate it and tell the user it exists, even without being able to summarize its contents.
- A large number of stored documents — same acceptable-for-now limitation as Memory's recall: retrieval scans metadata, not a search index, so it may degrade at large scale.

## Functional requirements

- FR-1: The system MUST retrieve documents by reasoning over their metadata (title, original filename), not a keyword/full-text index.
- FR-2: The system MUST NOT fabricate a document that was never added.
- FR-3: The system MUST behave correctly (no error, no fabrication) when the store is empty or nothing matches.
- FR-4: Reading/summarizing document content, where the format allows it, is in scope; content-level full-text search across all documents is OUT OF SCOPE (see epic's out-of-scope list).

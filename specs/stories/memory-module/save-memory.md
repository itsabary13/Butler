# Story: Save a memory

## User story

As a Jarvis user, I want to tell the AI something and have it remembered, so that I don't have to repeat context in future conversations.

## Acceptance criteria

- **Given** the user shares a piece of information worth remembering, **when** the AI decides (or the user explicitly asks) to save it, **then** the information is written to the wiki as a new page or merged into an existing related page (per `docs/db/memory-module.md`'s page/linking convention).
- **Given** a new memory relates to an existing wiki page, **when** it is saved, **then** the AI cross-references it with a `[[wiki-link]]` rather than creating a redundant, disconnected page.
- **Given** a memory is saved, **when** the save completes, **then** the user can tell (via a brief acknowledgment) that it was remembered, without needing to inspect the file system.

## Edge cases

- Saving near-duplicate information that's already captured on an existing page (should update/extend that page, not create a duplicate — this is "merge," not the deferred "Update memory" capability, since it happens as part of the create flow, not as a standalone edit operation).
- Saving information with no clear topical home (no existing related page) — a new page must still be created rather than the save being silently dropped.
- Very short or ambiguous input (e.g. a single word) — the AI should still capture it if the user clearly intends it as something to remember.
- Saving fails (e.g. disk write error) — the user must be told the save did not succeed; a silent failure is unacceptable.

## Functional requirements

- FR-1: The system MUST persist new information as Markdown page(s) under the wiki storage location defined by `docs/db/memory-module.md`.
- FR-2: The system MUST check for topically related existing pages before creating a new one, and link or merge accordingly.
- FR-3: The system MUST NOT require a server process or database to complete a save (per the epic's fixed constraints).
- FR-4: The system MUST surface a clear success or failure signal to the user for every save attempt.
- FR-5: Tagging (structured metadata beyond wiki-links) and explicit standalone "update"/"delete" operations are OUT OF SCOPE for this story (see epic's deferred list).

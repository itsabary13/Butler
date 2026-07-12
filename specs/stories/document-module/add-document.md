# Story: Add a document

## User story

As a Jarvis user, I want to give Jarvis an actual file (a PDF, Word document, image, etc.) and have it stored, so that I can ask for it back later without keeping track of where it lives on disk myself.

## Acceptance criteria

- **Given** the user provides a file (a path to an existing local file), **when** they ask Jarvis to add/save it as a document, **then** the original file is copied into the document store unmodified, alongside a small metadata record (title, original filename, added date).
- **Given** the user doesn't give an explicit title, **when** the document is added, **then** Jarvis infers a reasonable title from the filename/content and uses it as the topic.
- **Given** a document was added, **when** the add completes, **then** the user gets a brief acknowledgment — a silent add is unacceptable, same as Memory's save behavior.
- **Given** the referenced file doesn't exist or can't be read, **when** the user asks to add it, **then** Jarvis reports the failure clearly rather than silently doing nothing or fabricating a success.

## Edge cases

- Adding a file with the same title/topic as an already-stored document — since "Update/replace" is out of scope, this should be treated as a new, distinct document (disambiguated in its metadata/filename) rather than silently overwriting the original.
- Very large files — no explicit size limit is set for v1, but the acknowledgment should make clear if a copy took a long time or failed partway.
- Unsupported/unusual file types — still store the raw bytes and metadata even if Jarvis can't itself read the content (e.g. a proprietary binary format); retrieval later can still surface "here's the file" even without being able to summarize it.

## Functional requirements

- FR-1: The system MUST copy the original file's bytes unmodified into the document store — never re-encode, compress, or otherwise transform it.
- FR-2: The system MUST record metadata (title, original filename, added date) alongside the stored file.
- FR-3: The system MUST NOT require a server or database to complete an add (per the epic's fixed constraints).
- FR-4: The system MUST surface a clear success or failure signal for every add attempt.
- FR-5: Deleting, replacing, or editing an already-added document is OUT OF SCOPE for this story (see epic's out-of-scope list).

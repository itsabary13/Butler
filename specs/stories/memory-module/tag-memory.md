# Story: Tag a memory as Private or Work

## User story

As a Jarvis user, I want to optionally mark a memory as Private or Work when I save it, and later ask Jarvis to only consider one of those categories, so that I can keep personal and work information separately retrievable.

## Acceptance criteria

- **Given** the user shares information that's clearly personal/private or clearly work-related, **when** it's saved, **then** the page is tagged `private` or `work` accordingly.
- **Given** the user shares information with no clear Private/Work signal, **when** it's saved, **then** the page is saved untagged — tagging is never forced.
- **Given** the user asks a question that implies scoping to one category (e.g. "what do I have going on at work"), **when** `recall` runs, **then** only pages tagged with the matching category are considered relevant (untagged pages and the other category's pages are excluded from that specific filtered query).
- **Given** the user asks a general question with no Private/Work scoping implied, **when** `recall` runs, **then** all pages are considered regardless of tag, same as before this feature existed.
- **Given** a memory was saved before this feature existed (untagged), **when** the user asks a general (non-filtered) question, **then** it's still retrievable exactly as before — untagged memories are not hidden by default.

## Edge cases

- A query that's ambiguous about scope (e.g. mentions both personal and work context) — default to no filtering (treat as general) rather than guessing wrong and hiding relevant results.
- Filtered recall (e.g. "just my Work stuff") when no pages carry that tag yet — must behave like the existing empty-wiki edge case (no error, no fabrication), not treat the tag filter itself as an error condition.
- The user asking to retag or edit an existing memory's tag — out of scope for this increment; if directly asked, say so rather than attempting it (see epic's v1.1 out-of-scope note).

## Functional requirements

- FR-1: `remember` MUST support an optional `tag` value of `private`, `work`, or absent — never any other value.
- FR-2: `remember` MUST NOT require a tag on every save; the default when no Private/Work signal is present is untagged.
- FR-3: `recall` MUST support filtering candidate pages by `tag` when the query implies a scope, and MUST include all pages (tagged and untagged) when no scope is implied.
- FR-4: This increment MUST NOT implement retagging/editing an existing page's tag, deleting a page, or a standalone "Link related memories" feature — those remain deferred per the epic.

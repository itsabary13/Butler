# Story: Retrieve memories via AI-assisted search

## User story

As a Jarvis user, I want to ask a question and have the AI recall relevant things I've told it before, so that I benefit from continuity across conversations without manually re-explaining context.

## Acceptance criteria

- **Given** the wiki contains one or more pages, **when** the user asks something that relates to saved information, **then** the AI browses the wiki (reading candidate pages and following `[[wiki-links]]`) and incorporates relevant content into its answer.
- **Given** a query relates to a page that itself links to other pages, **when** retrieving, **then** the AI follows those links to gather connected context rather than stopping at the first matching page.
- **Given** no saved page is relevant to the query, **when** the AI searches, **then** it proceeds without fabricating a memory, and may say nothing was found if directly asked.
- **Given** multiple pages are plausibly relevant, **when** retrieving, **then** the AI uses judgment to select and synthesize the relevant ones rather than dumping every page verbatim.

## Edge cases

- Empty wiki (no memories saved yet) — retrieval must degrade gracefully (no error, no fabricated result).
- Query relevant to many pages (broad topic) — the AI should synthesize rather than overwhelm the user with raw page dumps.
- Query terms that are a near-miss for an existing page's topic (e.g. synonyms, rephrasing) — reasoning-based retrieval should still surface it, unlike a strict keyword match.
- Very large number of wiki pages — retrieval approach must remain "AI browses relevant pages," not require reading the entire wiki verbatim into context every time (an efficient browsing strategy, e.g. scanning page titles/links first, is left to `architect`/`backend-developer` to design).

## Functional requirements

- FR-1: The system MUST retrieve information by having the AI read wiki pages and reason about relevance — no keyword index, embedding store, or vector database (per the epic's fixed constraints).
- FR-2: The system MUST be able to follow `[[wiki-link]]` references from an initially-found page to gather connected context.
- FR-3: The system MUST NOT fabricate memories that were never saved.
- FR-4: The system MUST behave correctly (no error, no fabrication) when the wiki is empty or no relevant page exists.
- FR-5: Structured/filtered search (by tag, by explicit link graph query) is OUT OF SCOPE for this story (see epic's deferred list — Tag/Link are v1.1+).

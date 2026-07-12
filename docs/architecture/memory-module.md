# Architecture: Memory Module

## Module boundaries

The Memory Module is self-contained — it's the first epic and has no existing sibling modules to integrate with yet. Two capabilities from the stories map to two logical components, both operating against one shared component:

1. **Memory Writer** — implements the Save story (`specs/stories/memory-module/save-memory.md`).
2. **Memory Retriever** — implements the Retrieve story (`specs/stories/memory-module/retrieve-memory.md`).
3. **Wiki Store** — the shared Markdown-page storage both components read/write (see Domain Model / Database Design for its structure).

## Runtime model — key decision

There is no server process (fixed constraint in the epic). The Memory Module's "backend" is realized as **Claude Code Skills** — not process-scaffolding skills like the ones in this repo's `.claude/skills/` (which are deliberately manual-only), but *product* skills that are part of Jarvis itself:

- **`remember`** skill — implements the Memory Writer. `disable-model-invocation: false` (the default) — Claude may invoke it proactively during ordinary conversation when it judges something is worth remembering, without the user needing to run a slash command.
- **`recall`** skill — implements the Memory Retriever. Same: `disable-model-invocation: false` — Claude browses the Wiki Store proactively when answering, so memory "just works" in conversation.

This was an open UX/privacy fork (auto-invocation vs. manual `/remember`/`/recall`) — resolved by the user in favor of auto-invocation. `backend-developer` should write each skill's `description` field carefully (per Claude Code skill-authoring conventions) since, unlike this repo's manual-only process skills, the trigger phrasing in the description is what actually causes Claude to invoke these during real conversations.

## Components & data flow

```
User message
   |
   v
Claude (Jarvis) -- reads --> [recall skill] -- browses --> Wiki Store (Markdown pages, [[wiki-links]])
   |                                                              ^
   +-- decides info worth saving --> [remember skill] -- writes/merges --+
```

No network boundary exists anywhere in this flow — everything happens in-process, reading/writing local files during a Claude Code session.

Proposed physical location for the Wiki Store: `backend/memory-module/wiki/` (default-only — `database-designer` owns and can override the final naming/location convention).

## Technology / data-layer decision

- Storage: local Markdown files in a wiki pattern, per the epic's fixed constraint. No database engine, no ORM, no migrations.
- No server process, no REST/network boundary, no client-server split.
- No embedding or vector store — retrieval is Claude reading files directly and reasoning about relevance.

## Non-functional constraints

- **Privacy**: memory data is local-only by construction. Because personal memories are a different sensitivity class than this repo's process-scaffolding docs, flagging for `database-designer`/`reviewer`: consider whether the Wiki Store directory needs a `.gitignore` entry so personal memory content isn't accidentally committed/pushed to a shared remote.
- **Scalability**: wiki-browsing retrieval (no index) means retrieval cost/quality degrades as the number of pages grows. Acceptable for v1 (matches the retrieve-memory story's large-wiki edge case) and called out as a known limitation rather than solved now — revisit only if it becomes a real problem.
- **Portability**: plain Markdown means the wiki is human-readable and editable outside Claude Code too.
- **Durability**: since the wiki is gitignored from the main repo (per the privacy note above), it isn't backed up anywhere by default — losing the machine means losing the data. Resolved by giving `wiki/` its own independent git repo, pushed to a separate **private** GitHub repo (`backend/memory-module/README.md` has the URL) — kept fully separate from the public-facing project repo so memory content is never exposed alongside project scaffolding. (v1.2: `remember` now pushes automatically after every save, opt-out per save via "no push.")

## Downstream stage applicability

- **API Design: Not Applicable.** No server/network boundary exists — there is no request/response contract to design. `api-designer` should record this and point back here.
- **Database Design: Redirected, not skipped.** No conventional schema applies. `database-designer` instead defines the wiki's page-naming/slug convention, the `[[wiki-link]]` cross-referencing rule, merge-vs-create-page logic, and confirms (or overrides) the proposed storage path above.
- **UI: Expected Not Applicable for v1.** Interaction is purely conversational through Claude Code chat — save/recall happen as a byproduct of normal conversation, not through a dedicated screen. `frontend-developer` should confirm this explicitly rather than build a UI nobody asked for.

## v1.1 addendum — Tag memories (`specs/stories/memory-module/tag-memory.md`)

No new components and no change to the runtime model above. The addition is a data attribute plus a query-time behavior:

- **Memory Writer** (`remember`) now optionally records a `tag` (`private` | `work` | absent) as part of the same write it was already doing — no new component.
- **Memory Retriever** (`recall`) now optionally narrows its candidate scan to pages matching a tag, when the query implies that scope — still no index, still Claude reasoning about relevance, just over a filtered candidate set instead of all pages.

Still no server, no API, no UI. `database-designer` owns the frontmatter representation of `tag`; `backend-developer` owns how `remember` infers a tag and how `recall` detects filtering intent from a query.

**Note for `reviewer`**: "Private" as a self-reported, unenforced tag doesn't add any actual access control — it's a retrieval convenience, not a security boundary. There's nothing stopping `recall` (or a bug in it) from surfacing a Private-tagged memory in an unfiltered query, same as any other page. Worth reviewing once implemented, not blocking the design.

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `domain-designer` (`/domain-designer`) — this epic has a real (if small) domain model: a Wiki Page entity and its link relationships (v1.1 adds the `tag` field).

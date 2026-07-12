---
name: recall
description: Retrieves and uses previously saved memories to inform a response. Use whenever the current conversation could benefit from something the user has told Claude before — e.g. the user asks a question, asks for a recommendation, or references something that sounds like previously stored personal or project information ("what's my...", "remember when I said...", "what did I decide about...").
disable-model-invocation: false
---

# Recall

Implements the Memory Retriever component of the Memory module (`docs/architecture/memory-module.md`), against the wiki file format defined in `docs/db/memory-module.md`. Satisfies the acceptance criteria and functional requirements in `specs/stories/memory-module/retrieve-memory.md` and (v1.1) `specs/stories/memory-module/tag-memory.md`.

## Storage location

`backend/memory-module/wiki/<slug>.md`. If this directory doesn't exist or is empty, there are no memories yet — proceed without error and without fabricating anything.

## Steps

1. **Scan candidates.** List the pages under `backend/memory-module/wiki/` (titles/slugs are enough for an initial pass — no need to read every file in full up front).
2. **Check for a tag filter (v1.1).** Decide whether the query clearly implies scoping to one category — e.g. "what do I have going on at work", "anything Work-related about X" implies `work`; "my personal/private stuff about X" implies `private`. If the query is a general question with no such signal, or if it ambiguously mixes both, **do not filter** — consider all pages regardless of tag, same as before this feature existed. When a filter does apply, exclude pages whose `tag` doesn't match (this also excludes untagged pages from that specific filtered query).
3. **Identify relevant page(s).** Within whatever candidate set step 2 left you, reason about which page(s), if any, relate to the current query — by title/topic match or semantic relevance, not strict keyword matching.
4. **Read the relevant page(s) in full.**
5. **Follow links.** If a page's content contains `[[slug]]` references to other pages, and those linked pages are also plausibly relevant to the query, read them too — the link graph is written bidirectionally (`docs/db/memory-module.md`), so a connection is discoverable from either page.
6. **Synthesize, don't dump.** Use the relevant content to inform your response in your own words; don't paste raw page content verbatim unless the user is asking to see the memory directly.
7. **Never fabricate.** If nothing in the wiki is relevant, answer without inventing a memory that wasn't saved. If the user directly asks whether something is remembered and it isn't, say so.

## Explicitly out of scope

Explicit link-graph queries (e.g. "show me everything linked to X") — see `specs/epics/memory-module.md`'s out-of-scope list. Tag-based filtering is in scope (v1.1, step 2 above); free-text keyword/full-text search remains out of scope (retrieval is always AI-assisted reasoning, never a literal string match).

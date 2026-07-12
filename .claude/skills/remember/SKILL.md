---
name: remember
description: Saves information the user shares so it can be recalled in future conversations. Use whenever the user shares a fact, preference, plan, or other durable information worth remembering — either explicitly ("remember that...", "don't forget...", "note for later...") or implicitly when the user shares personal or project information Claude should retain (e.g. "my flight is at 6am on the 14th", "I prefer terse commit messages").
disable-model-invocation: false
---

# Remember

Implements the Memory Writer component of the Memory module (`docs/architecture/memory-module.md`), against the wiki file format defined in `docs/db/memory-module.md`. Satisfies the acceptance criteria and functional requirements in `specs/stories/memory-module/save-memory.md` and (v1.1) `specs/stories/memory-module/tag-memory.md`.

## Storage location

`backend/memory-module/wiki/<slug>.md` — create the directory if it doesn't exist yet.

## Steps

1. **Identify the topic.** Decide what concept/topic the new information belongs to, and derive a candidate `title`/`slug` (kebab-case of the title).
2. **Check for an existing related page.** List the files under `backend/memory-module/wiki/` and read titles/content of any that plausibly relate to the new information's topic — do not assume there's no match without checking.
3. **Merge or create:**
   - **If a related page exists**: append the new information as a new paragraph (or subsection) to that page's `content`, and set `updated_at` to now. Do not overwrite existing content. If the new information also relates to a second existing page, add a bidirectional `[[slug]]` link between the merged-into page and that second page (write the link in both files' content).
   - **If no related page exists**: create `<slug>.md` with frontmatter `slug`, `title`, `created_at` = `updated_at` = now, optional `tag` (see below), and the new information as `content`.
4. **Never produce a dangling link** — only write `[[slug]]` references to pages that exist at the time of writing (per the domain invariant in `docs/domain/memory-module.md`).
5. **Never leave `content` empty** — if there's truly nothing substantive to save, don't create/modify a page; say so instead of writing an empty page.
6. **Confirm the outcome to the user** briefly (e.g. "Got it, I'll remember that" / "Added that to what I know about X") — a save must never happen silently with no acknowledgment, and a failed write must be reported, not swallowed.

## Tagging (v1.1 — new pages only)

When **creating a new page**, decide whether the information clearly reads as `private` (personal, non-work) or `work` (job/professional context). Set `tag` to whichever clearly applies. If there's no clear signal either way, **omit the field entirely** — tagging is optional and must never be forced or guessed weakly. Never set both, never invent a third value.

This only applies at creation. When **merging** into an existing page, leave that page's existing `tag` value untouched — retagging an already-saved page is out of scope for this increment (see `tag-memory.md`'s out-of-scope note).

## Explicitly out of scope

Retagging/editing an existing page's tag, standalone update/delete operations, "Link related memories" as its own feature, and any UI beyond this conversational flow — see `specs/epics/memory-module.md`'s out-of-scope lists (v1 and v1.1). Don't implement them speculatively.

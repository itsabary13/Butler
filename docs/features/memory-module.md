# Feature: Memory Module

Jarvis can remember things you tell it and recall them later — no commands needed, it happens as part of normal conversation.

## What it does

- **Remembers automatically.** Tell Jarvis a fact, preference, or plan worth keeping — explicitly ("remember that...") or just by mentioning it — and it saves the information for future conversations.
- **Recalls automatically.** Ask a question that relates to something you've told it before, and Jarvis looks through what it remembers and answers using that context — without you needing to ask it to "search" anything.
- **Optional Private/Work tagging.** When you save something that's clearly personal or clearly work-related, Jarvis tags it accordingly. You can then ask a work-scoped question ("what do I have going on at work?") and it will only draw on Work-tagged memories for that answer. Untagged memories (most of them, day to day) are unaffected and still show up in ordinary, unfiltered questions.

## How it works, briefly

Memories are stored as a small wiki of Markdown pages — one page per topic, not one entry per thing you say. Related information gets merged into the same page over time rather than scattered across duplicates, and pages can cross-reference each other. There's no database and no server: it's just local files Jarvis reads and writes directly, which also means you can open and read them yourself if you ever want to.

## Known limitations (deferred, not yet built)

- **No editing or deleting** a memory once saved, and no retagging a memory after the fact — if something needs to change, for now that requires a future increment.
- **No explicit "link these together" or "tag this" command** — tagging only happens automatically at save time based on how you phrased it; linking between pages only happens as a side effect of merging related information, not as a feature you can trigger directly.
- **Retrieval doesn't scale to a huge number of memories yet** — recall works by reading through candidate pages, not an index, so it may get slower/less precise as the wiki grows very large. Not a problem at current scale.
- **"Private" is a label, not a lock.** Tagging something Private helps recall filter it out of Work-scoped questions, but it isn't real access control — there's no separate audience or account boundary being protected today.

## Where things live (for reference)

- `specs/epics/memory-module.md` — full scope and decision history
- `.claude/skills/remember/`, `.claude/skills/recall/` — the actual implementation
- `backend/memory-module/wiki/` — your saved memories (not committed to git — this is personal data, kept local only)

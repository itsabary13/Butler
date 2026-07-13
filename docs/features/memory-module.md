# Feature: Memory Module

Jarvis can remember things you tell it and recall them later — no commands needed, it happens as part of normal conversation.

## What it does

- **Remembers automatically.** Tell Jarvis a fact, preference, or plan worth keeping — explicitly ("remember that...") or just by mentioning it — and it saves the information for future conversations.
- **Recalls automatically.** Ask a question that relates to something you've told it before, and Jarvis looks through what it remembers and answers using that context — without you needing to ask it to "search" anything.
- **Optional Private/Work tagging.** When you save something that's clearly personal or clearly work-related, Jarvis tags it accordingly. You can then ask a work-scoped question ("what do I have going on at work?") and it will only draw on Work-tagged memories for that answer. Untagged memories (most of them, day to day) are unaffected and still show up in ordinary, unfiltered questions.
- **Backed up automatically.** Every save is also pushed to a private backup so it survives a machine change — you don't need to do anything for this to happen. Say "no push" in a specific save's message if you want that one save kept local-only.
- **Calendar sync.** Ask Jarvis to sync your calendar (or just ask what's coming up), and it pulls upcoming events from your primary Google Calendar for the next 7 days by default. This doesn't send reminders or alerts — it only refreshes what Jarvis knows, so it can answer when you ask. Re-sync anytime to refresh with new/changed events.
- **Structured reminders.** When you tell Jarvis something with both a date/recurrence and an action ("every 10th I need to deposit the rent check"), it's captured in a dedicated `reminders.md` list, not just as a regular memory. This is the storage half of a proactive-notification feature — actual phone alerts aren't built yet (see Known limitations).

## How it works, briefly

Memories are stored as a small wiki of Markdown pages — one page per topic, not one entry per thing you say. Related information gets merged into the same page over time rather than scattered across duplicates, and pages can cross-reference each other. There's no database and no server: it's just local files Jarvis reads and writes directly, which also means you can open and read them yourself if you ever want to.

## Known limitations (deferred, not yet built)

- **No editing or deleting** a memory once saved, and no retagging a memory after the fact — if something needs to change, for now that requires a future increment.
- **No explicit "link these together" or "tag this" command** — tagging only happens automatically at save time based on how you phrased it; linking between pages only happens as a side effect of merging related information, not as a feature you can trigger directly.
- **Retrieval doesn't scale to a huge number of memories yet** — recall works by reading through candidate pages, not an index, so it may get slower/less precise as the wiki grows very large. Not a problem at current scale.
- **"Private" is a label, not a lock.** Tagging something Private helps recall filter it out of Work-scoped questions, but it isn't real access control — there's no separate audience or account boundary being protected today.
- **No proactive reminders yet.** Calendar sync and `reminders.md` only refresh/store data for later Q&A — Jarvis won't alert you at a specific time on its own. Validated (see `docs/workflow.md`'s mobile-access brainstorm) that real phone alerts need a durable scheduled routine plus a genuine send channel (Telegram, chosen); that delivery piece is blocked on the user setting up a Telegram bot and isn't wired up yet.
- **Calendar sync is primary-calendar-only, upcoming-events-only, one page.** Not your shared/family calendars, not past events, and syncing again fully replaces the prior snapshot rather than keeping history.

## Where things live (for reference)

- `specs/epics/memory-module.md` — full scope and decision history
- `.claude/skills/remember/`, `.claude/skills/recall/`, `.claude/skills/sync-calendar/` — the actual implementation
- `backend/memory-module/wiki/` — your saved memories. Excluded from the main Butler repo (this is personal data, not project scaffolding) but automatically backed up to its own separate private GitHub repo (`butler-memory`) — see `backend/memory-module/README.md` for the restore steps on a new machine.

---
name: sync-calendar
description: Pulls upcoming events from the user's primary Google Calendar into their memory wiki, so Jarvis can answer questions about their schedule. Use whenever the user asks to sync/check their calendar, or asks what's coming up / what they have scheduled today, this week, tomorrow, etc. (e.g. "sync my calendar", "what's on my calendar this week", "do I have anything coming up?"). Does NOT send reminders or notifications — that's a separate, not-yet-built feature; this only refreshes what Jarvis knows so it can answer when asked.
disable-model-invocation: false
---

# Sync Calendar

Extends the Memory module (`docs/architecture/memory-module.md`) with a calendar-backed source for one reserved wiki page, per `docs/domain/memory-module.md`'s and `docs/db/memory-module.md`'s v1.3 notes. This is an exception to `remember`'s merge-only rule — see those docs before changing this skill's replace behavior.

## Scope (fixed — do not expand without the user's say-so)

- **Calendar**: the user's primary calendar only (`itsabary@gmail.com`), never other calendars (shared/family/holiday calendars) unless explicitly asked.
- **Events**: upcoming only (from now forward) — never past events, never `BIRTHDAY`-type events (those are handled separately, per the one-time birthday import; use `list_events`'s default `eventType` filter, which already excludes `BIRTHDAY`).
- **Window**: default 7 days ahead. If the user specifies a different window in their request ("tomorrow," "just today," "the next 3 days"), use that instead for this sync.
- **No reminders/notifications.** This skill only refreshes stored data for later Q&A — it never proactively alerts the user. If asked for real proactive reminders, say that's a separate feature that doesn't exist yet, don't attempt to fake it.

## Storage location

`backend/memory-module/wiki/upcoming-events.md` — a single reserved page, fixed slug, never disambiguated even on an apparent "collision" (there is no collision; this page always refers to itself).

## Steps

1. **Determine the window** (default 7 days, or per the user's request).
2. **Fetch events**: `list_events` on `itsabary@gmail.com`, `startTime` = now, `endTime` = now + window, reasonable `pageSize` (a week of events won't need pagination in practice).
3. **Build the content**: one line per event, chronologically sorted — title, date/time, location if present. If zero events are in range, write a short line like "No upcoming events in the next N days." — never leave `content` empty (domain invariant).
4. **Check whether `upcoming-events.md` already exists**:
   - **Exists**: keep its `created_at` unchanged, set `updated_at` to now, and **replace the entire body** with the freshly built content — do not append to the old list (old entries are stale by definition once superseded).
   - **Doesn't exist**: create it with `created_at` = `updated_at` = now, `title: Upcoming Events`, and the built content.
5. **Confirm the outcome to the user** briefly (e.g. "Synced N events for the next 7 days") — same no-silent-writes rule as `remember`.
6. **Back up automatically**, same as `remember`/`add-document`: commit and push the memory wiki's backup repo (`https://github.com/itsabary13/butler-memory`) from inside `backend/memory-module/wiki/` after a successful sync, unless the user's message says something like "no push" for this sync.

## Explicitly out of scope

Reminders/notifications of any kind; syncing calendars other than the primary one; syncing past events; editing/deleting individual synced events (the whole page is replaced as a unit, never edited piecemeal).

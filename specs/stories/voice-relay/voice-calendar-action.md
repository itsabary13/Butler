# Story: Create a calendar event by voice

## User story

As the Butler user, I want to ask, by voice, for something to be scheduled, and have it actually appear on my Google Calendar, so that I can manage my calendar without touching a computer.

## Acceptance criteria

- **Given** a transcribed request clearly describes a new event (e.g. "schedule lunch with [name] next Wednesday at one"), **when** the relay processes it, **then** a real event is created on the primary Google Calendar with a correct date/time.
- **Given** the event creation succeeds, **when** the relay replies, **then** the spoken confirmation states what was scheduled and when, not just a generic "done."
- **Given** the request is ambiguous about date/time, **when** the relay processes it, **then** it asks a clarifying question (via the same voice round-trip) rather than guessing and creating a wrong event.

## Edge cases

- A request to change or cancel an existing event — out of scope for v1 (create-only, matching Memory's own precedent of deferring update/delete); the relay should say this isn't supported yet rather than attempting it or silently failing.
- A vague time reference ("sometime next week") with no further clarification available — don't create a placeholder event; ask instead.
- Google Calendar API call fails (auth expired, network error) — report the failure in the voice reply; never claim success when the event wasn't actually created.

## Functional requirements

- FR-1: The system MUST create real Google Calendar events via a direct Calendar API call (its own OAuth credentials), not by attempting to invoke Claude Code's Calendar connector (which is only available inside a Claude Code session).
- FR-2: The system MUST NOT support update or delete operations in this story — create-only.
- FR-3: The system MUST confirm the concrete result (event title, date/time) in its spoken reply, not a generic acknowledgment.
- FR-4: The system MUST NOT create an event from an ambiguous request without first clarifying — never guess a date/time silently.

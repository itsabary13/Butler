# UI Design: Memory Module

**No dedicated UI for v1.**

Per `docs/architecture/memory-module.md`, `remember` and `recall` are auto-invoked Claude Code skills operating during ordinary conversation — there is no screen, form, or dedicated interface. The user "saves" a memory by telling Claude something worth remembering, and "retrieves" one by asking a question Claude answers using the wiki (`docs/db/memory-module.md`). Both stories in `specs/stories/memory-module/` describe conversational interactions, not UI interactions — there is no user-facing acceptance criterion here that requires a screen.

If a later epic (e.g. a dedicated Jarvis app surface, per the master plan's later phases) wants to expose the wiki visually (browsing/editing pages directly), that would be a new epic with its own UI design, not an extension of this one.

## Lifecycle Status

See `specs/epics/memory-module.md` — both the UI and Implementation (frontend) stages are marked N/A off the back of this file; there is no `frontend/memory-module/` subfolder (per `frontend/README.md`'s stated convention for epics with no dedicated UI).

## Hand-off

Next: `test-engineer` (`/test-engineer`) once `backend-developer` has implemented `remember`/`recall`. (Since there's no frontend work, the natural order here is `backend-developer` next, then `test-engineer` — not frontend implementation.)

# UI Design: Document Module

**No dedicated UI for v1.**

Same reasoning as Memory (`docs/ui/memory-module.md`): `add-document`/`find-document` are auto-invoked Claude Code skills operating during ordinary conversation. The user "adds" a document by providing a file path and asking Jarvis to save it, and "retrieves" one by asking about it — both purely conversational.

If a later phase introduces a visual Jarvis surface (per the master plan), browsing/opening stored documents visually would be a new epic's UI concern, not an extension of this one.

## Lifecycle Status

See `specs/epics/document-module.md` — both the UI and Implementation (frontend) stages are marked N/A off the back of this file; there is no `frontend/document-module/` subfolder.

## Hand-off

Next: `backend-developer` (`/backend-developer`).

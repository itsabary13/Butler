---
name: frontend-developer
description: Designs the UI and then implements it for an epic. Use via /frontend-developer — the first invocation (no docs/ui/<slug>.md yet) produces the UI design, later invocations implement it in frontend/. Not applicable for epics with no user-facing UI (e.g. CLI/conversational-only).
disable-model-invocation: true
---

# Frontend Developer

You own the UI stage and frontend Implementation (see `docs/workflow.md`). Check whether `docs/ui/<slug>.md` already exists to know which phase you're in.

## Inputs

- `specs/stories/<slug>/*.md`, `docs/architecture/<slug>.md`, `docs/domain/<slug>.md`, `docs/api/<slug>.md` (if applicable).

## Outputs

- **Design phase** (no `docs/ui/<slug>.md` yet): create it — screens/components, key states (empty/loading/error), no code. If the epic has no dedicated UI (e.g. interaction is purely through Claude Code chat), state that explicitly instead of inventing one.
- **Implementation phase** (design doc exists): code under `frontend/<slug>/...`, matching the UI doc and the API contract.

## Checklist ("done")

- UI doc covers every user-facing story, or explicitly states there is no dedicated UI.
- Implementation matches the UI doc and API contract.
- Lifecycle Status box(es) checked — UI and Implementation may be tracked as two separate lines.

## Hand-off

Next: `test-engineer` (`/test-engineer`).

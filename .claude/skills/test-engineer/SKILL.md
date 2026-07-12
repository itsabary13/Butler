---
name: test-engineer
description: Writes automated tests for an epic's implementation against its acceptance criteria. Use via /test-engineer once backend and/or frontend implementation exists for a story, to add unit/integration tests and confirm they pass.
disable-model-invocation: true
---

# Test Engineer

You own the Tests stage, after Implementation (see `docs/workflow.md`).

## Inputs

- `specs/stories/<slug>/*.md` — the acceptance criteria to test against.
- Implemented code under `backend/<slug>/` and/or `frontend/<slug>/`.
- `docs/architecture/<slug>.md` for test conventions/framework choice.

## Outputs

- Tests colocated per the architecture's chosen convention (default, if unspecified: `backend/<slug>/tests/`, `frontend/<slug>/tests/`).
- `docs/tests/<slug>.md` — a short summary: what's tested, what's deliberately not (and why), and how to run the tests.

## Checklist ("done")

- Every acceptance criterion has at least one automated test.
- Tests pass.
- Coverage summary written.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `reviewer` (`/reviewer`).

---
name: reviewer
description: Reviews an epic's implementation, tests, and design docs for correctness, security, and architectural conformance. Use via /reviewer once implementation and tests are complete for a story or epic, before it's considered done.
disable-model-invocation: true
---

# Reviewer

You own the Review stage, after Tests (see `docs/workflow.md`).

## Inputs

Everything produced so far for the epic: `specs/epics/<slug>.md`, its stories, `docs/architecture|domain|api|db|ui|tests/<slug>.md`, and the actual code in `backend/` and `frontend/`.

## Outputs

Create or update `docs/reviews/<slug>.md`:
- Findings by severity (correctness, security, architecture-conformance).
- A pass/fail verdict against the Definition of Done: Specification, Acceptance criteria, Architecture updates, Tests, Documentation, Review.

## Checklist ("done")

- Every Definition of Done item is explicitly addressed — checked or flagged as a gap.
- No unresolved high-severity findings.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `technical-writer` (`/technical-writer`).

---
name: api-designer
description: Designs the REST/OpenAPI contract (endpoints, request/response schemas, error model) for an epic. Use via /api-designer once the domain model exists and the architecture calls for a network API. For epics whose architecture doc states no server exists, this skill records that explicitly rather than being skipped.
disable-model-invocation: true
---

# API Designer

You own the API Design stage, between Domain Model and Database Design (see `docs/workflow.md`).

## Inputs

- `docs/architecture/<slug>.md` — check first whether it marks API design as Not Applicable for this epic.
- `docs/domain/<slug>.md`.
- `specs/stories/<slug>/*.md`.

## Outputs

Create or update `docs/api/<slug>.md`:
- If applicable: endpoint list, HTTP methods, request/response shapes, status/error codes, versioning note.
- **If Not Applicable** (e.g. a wiki/local-file epic with no server): write a short doc stating "Not applicable for this scope — see `docs/architecture/<slug>.md`" instead of omitting the file. The Lifecycle Status trail must stay complete.

## Checklist ("done")

- Every story that requires client/server interaction has a corresponding endpoint, OR the doc explicitly states none exist and why.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `database-designer` (`/database-designer`).

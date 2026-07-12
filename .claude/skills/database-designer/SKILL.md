---
name: database-designer
description: Designs the persistence layer for an epic — a database schema and migrations, or, for epics whose data layer is a wiki rather than a database, the wiki's page structure. Use via /database-designer once the domain model exists.
disable-model-invocation: true
---

# Database Designer

You own the Database Design stage, between API Design and UI (see `docs/workflow.md`).

## Inputs

- `docs/architecture/<slug>.md` — check whether it specifies a conventional database, or a "wiki, not database" data layer.
- `docs/domain/<slug>.md`.

## Outputs

Create or update `docs/db/<slug>.md`. Two cases:

1. **Conventional database**: tables/collections, fields, indexes, constraints, migration notes. Every domain entity maps to a persistence structure.
2. **Wiki-as-data-layer** (e.g. the Memory module — see `specs/epics/memory-module.md`): document the wiki page structure instead of a schema —
   - Page/slug naming convention (one page per topic/concept, not one file per raw entry).
   - The `[[wiki-link]]` cross-referencing convention between pages.
   - How pages get created vs. merged/edited over time as related information arrives.
   - Where pages live on disk (propose a directory under the epic's backend module, e.g. `backend/<slug>/wiki/`, unless the architecture doc says otherwise).

If neither applies, state so explicitly with a one-line reason — do not invent unnecessary schema.

## Checklist ("done")

- Every domain entity has a persistence mapping (table, or wiki page type) — or an explicit N/A with reasoning.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `frontend-developer` (`/frontend-developer`) for UI design, then `backend-developer` for implementation.

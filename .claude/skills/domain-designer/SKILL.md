---
name: domain-designer
description: Defines entities, value objects, and relationships for an epic's domain model. Use via /domain-designer after architecture is set, to model what a Memory, Task, or other core object looks like and how objects relate.
disable-model-invocation: true
---

# Domain Designer

You own the Domain Model stage, between Architecture and API Design (see `docs/workflow.md`).

## Inputs

- `specs/epics/<slug>.md` and its stories under `specs/stories/<slug>/`.
- `docs/architecture/<slug>.md`.

## Outputs

Create or update `docs/domain/<slug>.md`:
- Entity list — for each entity, its fields with types, and its invariants (e.g. "a memory must have non-empty content").
- Relationships between entities, with cardinality (e.g. Memory ↔ Memory link graph, Memory ↔ Tag).
- A simple ER/class diagram in text form (mermaid or plain indented text is fine).

## Checklist ("done")

- Every noun in the stories' acceptance criteria maps to an entity or field.
- Relationships and cardinalities are stated.
- Invariants are captured.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `api-designer` (`/api-designer`) — unless `docs/architecture/<slug>.md` marked API design Not Applicable, in which case go straight to `database-designer` or `backend-developer` per the architecture doc's note.

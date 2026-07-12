---
name: architect
description: Defines the high-level architecture, module boundaries, and technology choices for an epic before domain/API/DB design begins. Use via /architect right after stories are approved for an epic, or when re-evaluating architecture after a scope change.
disable-model-invocation: true
---

# Architect

You own the Architecture stage — added to the lifecycle because the master plan's Definition of Done requires "Architecture updates" even though its stage list omitted it (see `docs/workflow.md`). You run after `requirements-analyst`, before `domain-designer`.

## Inputs

- `specs/epics/<slug>.md` (including any "Fixed constraints" section) and its stories under `specs/stories/<slug>/`.
- Other epics' `docs/architecture/*.md`, to stay consistent across modules (naming, layering, shared components).

## Outputs

Create or update `docs/architecture/<slug>.md`:
- Module boundaries and how this epic's components relate to existing ones.
- Component/data-flow description (a text or mermaid diagram is fine).
- Technology/data-layer decision — state it explicitly, including the "no server" or "wiki, not database" case when the epic's fixed constraints call for it.
- Non-functional constraints (performance, privacy, etc.) worth calling out.
- Which downstream stages (API Design, Database Design, UI) are **Not Applicable** for this epic, and why — so `api-designer`/`database-designer`/`frontend-developer` don't have to re-derive it.

## Checklist ("done")

- Every capability in the epic maps to a component.
- The storage/hosting model is stated explicitly, even when it's "local files / no server."
- Any skipped downstream stage is named with a one-line reason.
- Lifecycle Status box checked, artifact path filled in.

## Hand-off

Next: `domain-designer` (`/domain-designer`) — unless this epic has no meaningful domain model, in which case say so and point to whichever design stage does apply.

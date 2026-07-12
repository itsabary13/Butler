# Jarvis Development Workflow

This is a static reference, maintained by hand (no skill auto-edits this file — update it only when a skill or lifecycle stage is added/changed, not per-feature).

## The lifecycle

```
Idea → Epic → User Stories → Functional Requirements → Architecture →
Domain Model → API Design → Database Design → UI → Implementation →
Tests → Review → Documentation
```

Never skip directly to implementation.

Two corrections to the original master plan (`input/Jarvis-Claude-Code-Plan.md`), adopted project-wide:
- **Architecture** is an explicit stage (the source plan implied it via the Architect role and the Definition of Done, but omitted it from the stage list). It sits between Functional Requirements and Domain Model.
- **Functional Requirements** has no dedicated role in the source plan. It's folded into `requirements-analyst`'s output (a section in each story file) rather than adding an extra skill.

## Stage → Skill → Command → Output

| Stage | Skill | Command | Key output |
|---|---|---|---|
| Epic / Stories / Functional Requirements | requirements-analyst | `/requirements-analyst` | `specs/epics/`, `specs/stories/` |
| Architecture | architect | `/architect` | `docs/architecture/` |
| Domain Model | domain-designer | `/domain-designer` | `docs/domain/` |
| API Design | api-designer | `/api-designer` | `docs/api/` |
| Database Design | database-designer | `/database-designer` | `docs/db/` |
| UI | frontend-developer | `/frontend-developer` | `docs/ui/`, then `frontend/` |
| Implementation (backend) | backend-developer | `/backend-developer` | `backend/` |
| Implementation (frontend) | frontend-developer | `/frontend-developer` | `frontend/` |
| Tests | test-engineer | `/test-engineer` | `docs/tests/`, test files |
| Review | reviewer | `/reviewer` | `docs/reviews/` |
| Documentation | technical-writer | `/technical-writer` | `docs/features/` |

Every skill is manually invoked only (`disable-model-invocation: true`) — nothing runs automatically. You gate each stage on purpose by typing the matching slash command.

## Conventions

- **Slugs**: kebab-case of the epic/story title (`Memory module` → `memory-module`).
- **Granularity**: `specs/epics/<slug>.md` and `specs/stories/<slug>/<story-slug>.md` are per-story. Everything under `docs/<stage>/<slug>.md` is per-epic — one architecture/domain/API/DB/UI/tests/review doc per module, updated incrementally as stories land.
- **Lifecycle Status checklist**: every epic file carries a checklist (`- [ ] Stage — owner skill — artifact path`). Each skill checks its own box and fills in the artifact path when it finishes its stage. This is the only progress tracker for "what stage is this epic at."
- **N/A stages**: a skill may conclude its stage doesn't apply to a given epic (e.g. API/DB design for a local-only, no-server epic). It must still write a short doc saying so explicitly and why, rather than skipping the file or inventing unnecessary design.
- **Wiki-as-data-layer epics**: some epics (starting with Memory) use a self-maintained wiki of interlinked Markdown pages as their data layer instead of a database — the "Karpathy wiki-memory" pattern. For these, `database-designer` documents the wiki's page/slug naming and `[[wiki-link]]` cross-referencing convention instead of a schema, and `api-designer` documents that no network API exists.

## Definition of Done

Every feature must include: Specification, Acceptance criteria, Architecture updates, Tests, Documentation, Review.

## Starting point

See `specs/epics/memory-module.md` — the first epic, already seeded with its v1 scope and constraints. Run `/requirements-analyst` against it to begin.

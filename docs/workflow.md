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

## Full lifecycle vs. fast path

The full 12-stage lifecycle is for **new epics** and **substantial capability changes** — where getting the spec/architecture/domain model wrong is expensive to unwind.

For a **small increment to an epic that's already shipped** (a new optional field, a minor behavior tweak, anything reversible and cheap), don't run every stage as its own separate, fully-documented pass. Instead:

- Describe the change once (a short story addition is still worth writing — it's what keeps scope honest — but skip a big ceremony around it).
- Touch only the design docs that actually change, and edit them in place with a short addition rather than rewriting them. If a stage genuinely doesn't change (e.g. UI, API), don't add anything to that doc at all — no need to re-state "still N/A."
- Implement directly in the same pass as the design update, rather than treating each of Architecture/Domain/DB/Backend as a separate invocation-and-checkpoint.
- Cover it with tests proportional to the change (extend the existing test file/fixtures; don't build new infrastructure for a small addition) and a short review note appended to the epic's existing review doc, rather than a full new findings report.
- Fold the change into the epic's existing feature doc when `technical-writer` next runs, rather than writing a new one.
- Still update the epic's Lifecycle Status / add a one-line note so there's a record of what shipped — the artifact trail should be thinner, not absent.

Rule of thumb: if the change fits in one sitting and doesn't introduce a new component, server, or entity, it's a fast-path increment. If it does, it's substantial enough to warrant the full lifecycle.

## Conventions

- **Slugs**: kebab-case of the epic/story title (`Memory module` → `memory-module`).
- **Granularity**: `specs/epics/<slug>.md` and `specs/stories/<slug>/<story-slug>.md` are per-story. Everything under `docs/<stage>/<slug>.md` is per-epic — one architecture/domain/API/DB/UI/tests/review doc per module, updated incrementally as stories land.
- **Lifecycle Status checklist**: every epic file carries a checklist (`- [ ] Stage — owner skill — artifact path`). Each skill checks its own box and fills in the artifact path when it finishes its stage. This is the only progress tracker for "what stage is this epic at."
- **N/A stages**: a skill may conclude its stage doesn't apply to a given epic (e.g. API/DB design for a local-only, no-server epic). It must still write a short doc saying so explicitly and why, rather than skipping the file or inventing unnecessary design.
- **Wiki-as-data-layer epics**: some epics (starting with Memory) use a self-maintained wiki of interlinked Markdown pages as their data layer instead of a database — the "Karpathy wiki-memory" pattern. For these, `database-designer` documents the wiki's page/slug naming and `[[wiki-link]]` cross-referencing convention instead of a schema, and `api-designer` documents that no network API exists.

## Using Jarvis from your phone

No separate mobile app or server is needed — `claude.ai/code` (the Claude Code web app) works from a phone browser and connects to the same GitHub repo (`github.com/itsabary13/Butler`) this desktop session uses. Open `claude.ai/code`, open/continue the Butler project, and chat normally: `remember`, `recall`, `add-document`, `sync-calendar`, and `process-inbox` all auto-invoke the same way they do here, because it's the same skills operating on the same repo. There is nothing Jarvis-specific to set up for this — it's a property of Claude Code itself, not something built for this project.

## Definition of Done

Every feature must include: Specification, Acceptance criteria, Architecture updates, Tests, Documentation, Review.

## Starting point

See `specs/epics/memory-module.md` — the first epic, already seeded with its v1 scope and constraints. Run `/requirements-analyst` against it to begin.

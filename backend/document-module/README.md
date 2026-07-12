# Document Module — Backend

No conventional backend codebase (per `docs/architecture/document-module.md`, no server process). The implementation lives as two auto-invoked Claude Code skills:

- `.claude/skills/add-document/SKILL.md` — Document Writer
- `.claude/skills/find-document/SKILL.md` — Document Retriever

This directory holds only the runtime data they operate on:

- `files/` — each document's original file plus a `.md` metadata sidecar (`docs/db/document-module.md` defines the layout). Created on first add; not pre-populated. Gitignored from the main Butler repo — see root `.gitignore` — since stored documents are personal data, not project scaffolding.

  Not yet backed up to a separate private repo the way `backend/memory-module/wiki/` is (see its README) — the architecture doc flags this as a known gap to close once real documents exist, rather than solving preemptively.

# Document Module — Backend

No conventional backend codebase (per `docs/architecture/document-module.md`, no server process). The implementation lives as two auto-invoked Claude Code skills:

- `.claude/skills/add-document/SKILL.md` — Document Writer
- `.claude/skills/find-document/SKILL.md` — Document Retriever

This directory holds only the runtime data they operate on:

- `files/` — each document's original file plus a `.md` metadata sidecar (`docs/db/document-module.md` defines the layout). Created on first add; not pre-populated. Gitignored from the main Butler repo — see root `.gitignore` — since stored documents are personal data, not project scaffolding.

  It's its own independent git repository (nested but invisible to Butler's git, since the whole `files/` path is gitignored), backed up to a **separate private** GitHub repo: `https://github.com/itsabary13/butler-documents`. Restore on a new machine by cloning that repo's contents into `files/`. It is never pushed to or exposed via the public-facing Butler repo, same treatment as `backend/memory-module/wiki/`.

  `add-document` (v1.3) commits and pushes this repo automatically after every add, unless the user says something like "no push" for that specific add — same behavior as `remember`'s v1.2.

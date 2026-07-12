# Memory Module — Backend

There is no conventional backend codebase here (per `docs/architecture/memory-module.md`, this epic has no server process). The implementation lives as two auto-invoked Claude Code skills:

- `.claude/skills/remember/SKILL.md` — Memory Writer
- `.claude/skills/recall/SKILL.md` — Memory Retriever
- `.claude/skills/sync-calendar/SKILL.md` — Calendar Sync (v1.3): maintains one reserved page, `wiki/upcoming-events.md`, replaced wholesale on every sync (an explicit exception to the merge-only rule the other two skills follow)

This directory holds only the runtime data they operate on:

- `wiki/` — the Markdown wiki pages (`docs/db/memory-module.md` defines the file format and conventions). Created on first save; not pre-populated. Gitignored from the main Butler repo — see root `.gitignore` — since memory content is personal data, not project scaffolding.

  It's its own independent git repository (nested but invisible to Butler's git, since the whole `wiki/` path is gitignored), backed up to a **separate private** GitHub repo: `https://github.com/itsabary13/butler-memory`. This exists purely so memory data survives a machine change — clone that repo's contents into `wiki/` on a new machine to restore it. It is never pushed to or exposed via the public-facing Butler repo.

  `remember` (v1.2) and `sync-calendar` (v1.3) both commit and push this repo automatically after every save/sync, unless the user says something like "no push" for that specific action.

# Memory Module — Backend

There is no conventional backend codebase here (per `docs/architecture/memory-module.md`, this epic has no server process). The implementation lives as two auto-invoked Claude Code skills:

- `.claude/skills/remember/SKILL.md` — Memory Writer
- `.claude/skills/recall/SKILL.md` — Memory Retriever

This directory holds only the runtime data they operate on:

- `wiki/` — the Markdown wiki pages (`docs/db/memory-module.md` defines the file format and conventions). Created on first save; not pre-populated. Gitignored — see root `.gitignore` — since memory content is personal data, not project scaffolding.

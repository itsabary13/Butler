# API Design: Memory Module

**Not applicable for this scope.**

Per `docs/architecture/memory-module.md`, the Memory Module has no server process and no network boundary — `remember`/`recall` are Claude Code skills operating directly on local files, not a client/server split. There is no request/response contract to design.

See `docs/architecture/memory-module.md` for the full reasoning, and `docs/db/memory-module.md` for the persistence design that replaces this stage's usual output.

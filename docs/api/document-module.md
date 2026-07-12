# API Design: Document Module

**Not applicable for this scope.**

Per `docs/architecture/document-module.md`, the Document Module has no server process and no network boundary — `add-document`/`find-document` are Claude Code skills operating directly on local files, not a client/server split. There is no request/response contract to design.

See `docs/architecture/document-module.md` for the full reasoning, and `docs/db/document-module.md` for the persistence design that replaces this stage's usual output.

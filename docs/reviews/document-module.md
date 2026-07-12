# Review: Document Module

Reviewed: epic, both stories, architecture/domain/api/db/ui/tests docs, `.claude/skills/add-document/`, `.claude/skills/find-document/`, `backend/document-module/README.md`, and the test suite/fixtures.

## Findings

### High (found and fixed during this review) — Copy mechanism unspecified, risked corrupting binary files

`add-document`'s step 4 said "copy the file unmodified" without saying *how*. Reading a file through the model's text-based Read tool and writing it back out with the Write tool does not reliably preserve raw bytes for binary formats (PDF, images, Word documents) — exactly the formats this module exists for, per the user's stated intent. A future invocation could silently produce a corrupted or truncated document while still reporting success.

**Fixed**: `.claude/skills/add-document/SKILL.md` step 4 now explicitly requires a direct filesystem copy command (`cp`/`Copy-Item`), never a Read-then-Write round-trip through the model. Verified against the live smoke test, which already used `cp` for this reason.

### Medium — Documents aren't backed up, unlike Memory

`docs/architecture/document-module.md` flags this and deliberately defers it ("recommend the same fix... once this ships, rather than solving preemptively"). Given the user already raised durability concerns for Memory and a private backup repo exists for it, this is a real, known gap for real usage — not blocking, since it was a deliberate scope call already documented, but worth surfacing again now that the module actually exists: recommend deciding whether to extend the existing `butler-memory` backup repo or create a separate one, the next time a real document is added.

### Low — Slug collision disambiguation is underspecified

Same as Memory's original review finding: "disambiguate with a qualifier" doesn't say exactly how. Acceptable for v1 (mirrors Memory's accepted-as-is treatment of the same gap) — not a new problem introduced here.

### Low — `add-document`'s trigger description is broad

"hands over a file path with an intent to keep it" could over-trigger on casual file mentions. Mitigated the same way as Memory: every add is acknowledged to the user, never silent, so a wrong save is immediately visible and correctable.

## Security notes

No high-severity issues beyond the copy-mechanism bug above (fixed). No network surface (confirmed N/A in `docs/api/document-module.md`). Document content is correctly gitignored (`backend/document-module/files/`), consistent with Memory's treatment of personal data.

## Architecture-conformance notes

Implementation matches `docs/architecture/document-module.md`, `docs/domain/document-module.md`, and `docs/db/document-module.md`: no server/database introduced, metadata sidecar fields match the domain model exactly, slug sanitization correctly reuses Memory's established ASCII/transliteration rule rather than reinventing one.

## Definition of Done verdict

| Item | Status |
|---|---|
| Specification | Done — `specs/epics/document-module.md`, both stories |
| Acceptance criteria | Done — both stories |
| Architecture updates | Done — `docs/architecture/document-module.md` |
| Tests | Done — `docs/tests/document-module.md` (5/5 automated, plus a live smoke test) |
| Documentation | **Not yet** — expected; `technical-writer` runs next |
| Review | Done — this file |

**Verdict: PASS**, contingent on the binary-copy fix above (already applied). One follow-up recommendation (backup) to address opportunistically, not blocking.

## Lifecycle Status

See `specs/epics/document-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `technical-writer` (`/technical-writer`).

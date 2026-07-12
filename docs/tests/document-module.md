# Tests: Document Module

Same two-layer approach as Memory (`docs/tests/memory-module.md`), since the implementation is likewise two auto-invoked skills rather than conventional code.

## 1. Structural/invariant tests (automated, repeatable)

`backend/document-module/tests/validate_documents.py` checks metadata sidecars against the invariants in `docs/domain/document-module.md` and `docs/db/document-module.md`: required frontmatter fields, slug/filename match, non-empty notes body, and that each sidecar's paired file actually exists on disk.

`backend/document-module/tests/test_validate_documents.py` is a `unittest` suite over fixtures in `backend/document-module/tests/fixtures/`: one `valid/` document (sidecar + paired file, expect zero errors) and three `invalid/<case>/` fixtures (missing field, missing paired file, slug/filename mismatch).

**How to run:**
```
python backend/document-module/tests/test_validate_documents.py -v
```
**Result:** 5/5 tests pass.

## 2. Behavioral smoke test (manual, one-time)

1. Created a throwaway text file and invoked `add-document` against it. It correctly copied the file unmodified into `backend/document-module/files/` and wrote a matching metadata sidecar.
2. Ran `validate_documents.py` against the result — passed with no invariant violations.
3. Invoked `find-document` with a related query. It correctly scanned the single candidate sidecar, opened the paired file, and answered using its actual content (a fictional grocery list) without fabrication.
4. Deleted the throwaway document and sidecar afterward — it was test fixture data, not something the user asked to keep.

**Result:** add-then-retrieve round-trip works as specified in both stories, including reading a readable file format's actual content at retrieval time.

## What's deliberately not tested

- Non-text-readable formats (PDF, images) — the smoke test used a `.txt` file for simplicity. The `add-document`/`find-document` instructions handle other formats the same way structurally (copy bytes, read frontmatter), but reading actual PDF/image content live wasn't exercised here.
- Slug collision disambiguation (two documents sharing a topic/title) — not exercised live, only specified.
- Large numbers of documents — same acceptable-for-now limitation as Memory.
- Delete/replace, tagging, cross-linking to Memory — out of scope (see `specs/epics/document-module.md`), untested by design.

## Lifecycle Status

See `specs/epics/document-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `reviewer` (`/reviewer`).

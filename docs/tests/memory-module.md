# Tests: Memory Module

The Memory module's implementation is two auto-invoked Claude Code skills (`.claude/skills/remember/`, `.claude/skills/recall/`) rather than conventional application code, so testing splits into two layers.

## 1. Structural/invariant tests (automated, repeatable)

`backend/memory-module/tests/validate_wiki.py` checks any set of wiki pages against the invariants in `docs/domain/memory-module.md` and `docs/db/memory-module.md`: required frontmatter fields present, `content` non-empty, `slug` matches filename, no dangling `[[links]]`, `created_at <= updated_at`.

`backend/memory-module/tests/test_validate_wiki.py` is a `unittest` suite exercising the validator against fixtures in `backend/memory-module/tests/fixtures/`: one `valid/` pair of cross-linked pages (expect zero errors), and five `invalid/<case>/` fixtures, one per invariant violation (missing field, empty content, dangling link, bad timestamps, slug/filename mismatch — each expected to be individually detected).

**How to run:**
```
python backend/memory-module/tests/test_validate_wiki.py -v
```
**Result:** 7/7 tests pass.

## 2. Behavioral smoke test (manual, one-time — documents that the skills actually work end to end)

Since `remember`/`recall` are natural-language-instructed skills, not deterministic functions, their *judgment* (what to save, what's relevant) can't be unit tested — this was instead exercised live as a smoke test during this stage:

1. Invoked `remember` with a throwaway fact ("the user's favorite color is teal"). No existing wiki page existed, so it correctly created a new page (`favorite-color.md`) rather than forcing a merge.
2. Ran `validate_wiki.py` against the result — passed with no invariant violations, confirming the skill's real output matches the documented file format.
3. Invoked `recall` with a related query ("what's the user's favorite color?"). It correctly scanned the single candidate page, read it, and synthesized the answer ("teal") without fabrication.
4. Deleted the throwaway test page and the now-empty `wiki/` directory afterward — it was test fixture data, not a real memory the user asked to keep.

**Result:** save-then-retrieve round-trip works as specified in both stories.

## What's deliberately not tested

- Merge-vs-create judgment quality across many pages, and multi-hop link-following — acceptable to defer; the smoke test only exercised the single-page case. Revisit with more scenarios if `reviewer` or real usage surfaces a problem.
- Tag/Update/Delete/Link-as-a-feature — out of scope for v1 (see `specs/epics/memory-module.md`), so untested by design.

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `reviewer` (`/reviewer`).

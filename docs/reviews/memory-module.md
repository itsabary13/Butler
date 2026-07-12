# Review: Memory Module

Reviewed: epic, both stories, architecture/domain/api/db/ui/tests docs, `.claude/skills/remember/`, `.claude/skills/recall/`, `backend/memory-module/README.md`, and the test suite/fixtures.

## Findings

### Medium — Slug derivation has no specified sanitization (`.claude/skills/remember/SKILL.md`, `docs/db/memory-module.md`)

Step 1 of `remember` says to derive a slug by kebab-casing the title, but neither it nor the db doc specifies stripping/escaping characters outside `[a-z0-9-]`. Since the title originates from freeform conversational text, a pathological input could in principle kebab-case into something containing a path separator or `..`, risking a write outside `backend/memory-module/wiki/`. Low real-world likelihood in a single-user local session, but cheap to close off.

**Recommendation**: add one line to `docs/db/memory-module.md`'s slug convention: strip any character outside `[a-z0-9-]`, collapse repeated `-`, and treat an empty result as "no valid topic — ask the user to clarify" rather than writing a page with an unsafe or empty filename.

### Low-Medium — New pages never link to related-but-distinct existing pages

`docs/db/memory-module.md`'s create-vs-merge rule is binary: a page is either merged into an existing one, or created fresh with no link at all. There's no middle case for "related enough to cross-reference, not related enough to merge" — so two genuinely separate but topically adjacent memories (e.g. "favorite color" and "favorite programming language," both preferences) never end up connected in the graph. This narrows `recall`'s link-following (`retrieve-memory.md`'s FR-2) for anything short of a full merge.

Not a blocker — it's consistent with "Link related memories" being explicitly out of scope for v1 (`specs/epics/memory-module.md`). Flagging so it's a documented limitation rather than an implicit gap, and so the future Link epic knows this is unaddressed territory, not something v1 already partially solved.

### Low — `remember`'s auto-invocation description is broad

"implicitly when the user shares personal or project information Claude should retain" could trigger saves the user didn't consciously intend. Mitigated by `remember`'s step 6, which requires acknowledging every save (no silent writes) — the user always has visibility and a chance to correct a wrong save. Acceptable given the user's explicit choice of auto-invocation (see `docs/architecture/memory-module.md`); worth revisiting only if real usage shows over-eager saving.

### Low — `validate_wiki.py`'s frontmatter parser is a flat key:value splitter, not real YAML

Fine for the four flat scalar fields `docs/db/memory-module.md` currently defines. Whoever later extends the frontmatter (e.g. a `tags` list, if "Tag memories" ships) needs to upgrade the parser at the same time, or it will silently misparse the new field.

## Security notes

No high-severity issues found. The module has no network surface (confirmed N/A in `docs/api/memory-module.md`) and memory content is correctly gitignored (`backend/memory-module/wiki/`). The slug-sanitization gap above is the only concrete hardening item, and it's low-likelihood in this single-user, local context.

## Architecture-conformance notes

Implementation matches `docs/architecture/memory-module.md`, `docs/domain/memory-module.md`, and `docs/db/memory-module.md` in every case checked: no server/database was introduced, frontmatter fields match the domain model exactly (`links` correctly persisted as inline `[[slug]]` refs, not a duplicate frontmatter array), and the bidirectional-linking convention is implemented as specified in the merge path. The two findings above are gaps in what was specified, not deviations from it.

## Definition of Done verdict

| Item | Status |
|---|---|
| Specification | Done — `specs/epics/memory-module.md`, `specs/stories/memory-module/*.md` |
| Acceptance criteria | Done — both stories |
| Architecture updates | Done — `docs/architecture/memory-module.md` |
| Tests | Done — `docs/tests/memory-module.md` (7/7 automated tests pass, plus a documented live smoke test) |
| Documentation | **Not yet** — expected; `technical-writer` runs next |
| Review | Done — this file |

**Verdict: PASS**, with two follow-up recommendations (slug sanitization, and documenting the create/merge linking gap) to address opportunistically — neither is high-severity or blocks moving to Documentation.

## v1.1 addendum — Tag memories

Reviewed the tag increment: `tag-memory.md`, the `tag` field additions to the domain/db docs, `remember`/`recall`'s tag inference/filtering instructions, and the extended validator + smoke test in `docs/tests/memory-module.md`.

**Finding (Low, non-blocking, already flagged at design time)**: `docs/architecture/memory-module.md`'s v1.1 addendum correctly notes that `private` is a self-reported convenience tag, not real access control — nothing prevents an unfiltered `recall` query (or a bug in it) from surfacing a Private-tagged memory. No fix needed for v1.1's stated scope (there's no cross-user or cross-context boundary to protect yet, single user/session), but worth keeping in mind if Jarvis ever gains multiple profiles or shared contexts.

No new high-severity findings. Implementation matches the story and design docs: tagging is optional and creation-only (merge path correctly leaves existing tags untouched, matching the out-of-scope note), filtering correctly excludes untagged pages only from filtered queries and leaves general queries unaffected, and the validator now rejects any tag value other than `private`/`work`. **Verdict: PASS.**

## Lifecycle Status

See `specs/epics/memory-module.md` — this stage is checked off with this file as its artifact.

## Hand-off

Next: `technical-writer` (`/technical-writer`).

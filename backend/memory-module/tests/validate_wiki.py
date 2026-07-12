#!/usr/bin/env python3
"""Validates memory-module wiki pages against the invariants in
docs/domain/memory-module.md and docs/db/memory-module.md: required
frontmatter fields, non-empty content, slug/filename match, no
dangling [[links]], and created_at <= updated_at."""

import re
import sys
from pathlib import Path

REQUIRED_FIELDS = ["slug", "title", "created_at", "updated_at"]
LINK_PATTERN = re.compile(r"\[\[([a-z0-9-]+)\]\]")


def parse_page(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text, ["missing frontmatter block"]
    end = text.find("\n---", 4)
    if end == -1:
        return None, text, ["frontmatter block not closed"]
    fm_text = text[4:end]
    body = text[end + 4:].lstrip("\n")
    frontmatter = {}
    for line in fm_text.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            return None, body, [f"malformed frontmatter line: {line!r}"]
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body, []


def validate_page(path: Path, known_slugs: set) -> list:
    errors = []
    frontmatter, body, parse_errors = parse_page(path)
    errors.extend(parse_errors)
    if frontmatter is None:
        return errors

    for field in REQUIRED_FIELDS:
        if not frontmatter.get(field):
            errors.append(f"missing required frontmatter field: {field}")

    slug = frontmatter.get("slug")
    if slug and slug != path.stem:
        errors.append(f"slug '{slug}' does not match filename '{path.stem}.md'")

    if not body.strip():
        errors.append("content is empty")

    created_at = frontmatter.get("created_at")
    updated_at = frontmatter.get("updated_at")
    if created_at and updated_at and updated_at < created_at:
        errors.append(f"updated_at ({updated_at}) is before created_at ({created_at})")

    for linked_slug in LINK_PATTERN.findall(body):
        if linked_slug not in known_slugs:
            errors.append(f"dangling link: [[{linked_slug}]] does not exist")

    return errors


def validate_wiki(directory) -> dict:
    directory = Path(directory)
    if not directory.exists():
        return {}
    pages = sorted(directory.glob("*.md"))
    known_slugs = {p.stem for p in pages}
    results = {}
    for page in pages:
        errs = validate_page(page, known_slugs)
        if errs:
            results[page.name] = errs
    return results


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "wiki"
    results = validate_wiki(target)
    if not results:
        print(f"OK: no invariant violations found in {target}")
        return 0
    for filename, errs in results.items():
        for err in errs:
            print(f"{filename}: {err}")
    print(f"FAIL: {sum(len(v) for v in results.values())} violation(s) across {len(results)} file(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

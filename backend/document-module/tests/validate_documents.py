#!/usr/bin/env python3
"""Validates document-module metadata sidecars against the invariants in
docs/domain/document-module.md and docs/db/document-module.md: required
frontmatter fields, slug/filename match, non-empty body, and that each
sidecar's paired file (<slug>.<file_extension>) actually exists."""

import sys
from pathlib import Path

REQUIRED_FIELDS = ["slug", "title", "original_filename", "file_extension", "added_at"]


def parse_sidecar(path: Path):
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


def validate_sidecar(path: Path) -> list:
    errors = []
    frontmatter, body, parse_errors = parse_sidecar(path)
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
        errors.append("notes body is empty")

    ext = frontmatter.get("file_extension")
    if slug and ext:
        paired_file = path.parent / f"{slug}.{ext}"
        if not paired_file.exists():
            errors.append(f"paired file missing: {paired_file.name}")

    return errors


def validate_documents(directory) -> dict:
    directory = Path(directory)
    if not directory.exists():
        return {}
    results = {}
    for sidecar in sorted(directory.glob("*.md")):
        errs = validate_sidecar(sidecar)
        if errs:
            results[sidecar.name] = errs
    return results


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "files"
    results = validate_documents(target)
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

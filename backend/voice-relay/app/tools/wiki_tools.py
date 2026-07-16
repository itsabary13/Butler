"""Reads/writes backend/memory-module/wiki/ using the exact conventions
documented in docs/db/memory-module.md. This is a second implementation
against that shared file format, not a fork of it — a page written here
must be indistinguishable from one written by the `remember` skill.

Frontmatter parsing intentionally matches the flat key:value approach in
backend/memory-module/tests/validate_wiki.py (not a full YAML parser) —
the documented format only ever uses flat scalar fields.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.frontmatter import parse_page as _parse_page

LINK_PATTERN = re.compile(r"\[\[([a-z0-9-]+)\]\]")
SLUG_SAFE_PATTERN = re.compile(r"[^a-z0-9-]+")
VALID_SLUG = re.compile(r"^[a-z0-9-]+$")


class UnsafeSlugError(ValueError):
    """Raised when a slug supplied by the model doesn't match the safe
    [a-z0-9-]+ pattern — never let an unsanitized slug reach a file path
    (path traversal risk: the slug comes from tool-call arguments, which
    are ultimately model output derived from a voice transcript)."""


def _validate_slug(slug: str) -> str:
    if not VALID_SLUG.match(slug):
        raise UnsafeSlugError(f"unsafe slug rejected: {slug!r}")
    return slug


def wiki_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / settings.wiki_repo_path


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(title: str) -> str:
    """ASCII-only kebab-case, per docs/db/memory-module.md's sanitization rule.
    Non-ASCII input is dropped rather than transliterated here (a simpler,
    conservative subset of remember's behavior) — callers should pass an
    already-reasonable title."""
    ascii_title = title.encode("ascii", "ignore").decode("ascii").lower()
    slug = SLUG_SAFE_PATTERN.sub("-", ascii_title).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "untitled"


def _write_page(slug: str, title: str, content: str, tag: Optional[str],
                 created_at: str, updated_at: str) -> None:
    lines = [
        "---",
        f"slug: {slug}",
        f"title: {title}",
        f"created_at: {created_at}",
        f"updated_at: {updated_at}",
    ]
    if tag:
        lines.append(f"tag: {tag}")
    lines.append("---")
    lines.append("")
    lines.append(content.strip())
    lines.append("")
    (wiki_dir() / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")


def list_wiki_pages() -> list[dict]:
    """Cheap manifest: frontmatter only, no bodies. Mirrors recall's
    'scan candidates cheaply' step."""
    directory = wiki_dir()
    if not directory.exists():
        return []
    manifest = []
    for path in sorted(directory.glob("*.md")):
        frontmatter, _ = _parse_page(path)
        if frontmatter is None:
            continue
        manifest.append({
            "slug": frontmatter.get("slug", path.stem),
            "title": frontmatter.get("title", path.stem),
            "tag": frontmatter.get("tag"),
            "updated_at": frontmatter.get("updated_at"),
        })
    return manifest


def read_wiki_page(slug: str) -> Optional[dict]:
    """Full content of one page, plus any [[wiki-link]] slugs found in it —
    so the caller (the tool-use loop) can decide whether to follow them,
    same as recall's link-following step."""
    _validate_slug(slug)
    path = wiki_dir() / f"{slug}.md"
    if not path.exists():
        return None
    frontmatter, body = _parse_page(path)
    if frontmatter is None:
        return None
    return {
        "slug": frontmatter.get("slug", slug),
        "title": frontmatter.get("title", slug),
        "tag": frontmatter.get("tag"),
        "created_at": frontmatter.get("created_at"),
        "updated_at": frontmatter.get("updated_at"),
        "content": body.strip(),
        "linked_slugs": sorted(set(LINK_PATTERN.findall(body))),
    }


def save_memory(slug: str, title: str, content: str, tag: Optional[str] = None) -> dict:
    """Merge-or-create, mirroring remember's algorithm (docs/db/memory-module.md):
    merging into an existing page appends content and never touches its
    existing tag; creating a new page uses the given tag (if any)."""
    _validate_slug(slug)
    path = wiki_dir() / f"{slug}.md"
    now = now_iso()
    if path.exists():
        frontmatter, body = _parse_page(path)
        if frontmatter is None:
            raise ValueError(f"existing page {slug}.md has unparseable frontmatter")
        merged_body = body.strip() + "\n\n" + content.strip()
        _write_page(
            slug=slug,
            title=frontmatter.get("title", title),
            content=merged_body,
            tag=frontmatter.get("tag"),
            created_at=frontmatter.get("created_at", now),
            updated_at=now,
        )
        return {"action": "merged", "slug": slug}
    wiki_dir().mkdir(parents=True, exist_ok=True)
    _write_page(slug=slug, title=title, content=content, tag=tag, created_at=now, updated_at=now)
    return {"action": "created", "slug": slug}


def append_reminder(rule: str, description: str) -> dict:
    """Appends one line to the reserved reminders.md page — accumulates,
    never replaced (docs/domain/memory-module.md's v1.4 note)."""
    slug = "reminders"
    path = wiki_dir() / f"{slug}.md"
    now = now_iso()
    line = f"- {rule}: {description}"
    if path.exists():
        frontmatter, body = _parse_page(path)
        if frontmatter is None:
            raise ValueError("reminders.md has unparseable frontmatter")
        new_body = body.rstrip("\n") + "\n" + line
        _write_page(
            slug=slug,
            title=frontmatter.get("title", "Reminders"),
            content=new_body,
            tag=None,
            created_at=frontmatter.get("created_at", now),
            updated_at=now,
        )
        return {"action": "appended"}
    wiki_dir().mkdir(parents=True, exist_ok=True)
    _write_page(slug=slug, title="Reminders", content=line, tag=None, created_at=now, updated_at=now)
    return {"action": "created"}

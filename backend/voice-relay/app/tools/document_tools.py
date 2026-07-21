"""Document metadata lookup and (Telegram document uploads, v1.4) saving,
reusing the sidecar format documented in docs/db/document-module.md exactly
— a page/sidecar written here must be indistinguishable from one written by
the add-document skill. No binary delivery *over voice* (an unchanged
specs/epics/voice-relay.md out-of-scope item — a saved document can still
be retrieved by other means, just not spoken).
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings
from app.frontmatter import parse_page  # same flat frontmatter format
from app.tools.wiki_tools import slugify  # same ASCII kebab-case rule (docs/db/document-module.md)

VALID_EXT = re.compile(r"^[a-z0-9]{1,10}$")


def docs_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / settings.docs_repo_path


def list_document_metadata() -> list[dict]:
    directory = docs_dir()
    if not directory.exists():
        return []
    manifest = []
    for path in sorted(directory.glob("*.md")):
        if path.name.startswith("."):
            continue
        frontmatter, _ = parse_page(path)
        if frontmatter is None:
            continue
        manifest.append({
            "slug": frontmatter.get("slug", path.stem),
            "title": frontmatter.get("title", path.stem),
            "original_filename": frontmatter.get("original_filename"),
            "added_at": frontmatter.get("added_at"),
        })
    return manifest


def find_document(query: str) -> list[dict]:
    """Simple substring match over title/filename — the model is expected
    to reason about relevance itself using list_document_metadata's full
    manifest; this is a convenience filter, not the primary mechanism."""
    query_lower = query.lower()
    return [
        doc for doc in list_document_metadata()
        if query_lower in (doc["title"] or "").lower()
        or query_lower in (doc["original_filename"] or "").lower()
    ]


def _unique_slug(base_slug: str, directory: Path) -> str:
    """Disambiguates with a numeric qualifier on collision with an
    unrelated existing document — never silently overwrites
    (docs/db/document-module.md's Add flow)."""
    slug = base_slug
    n = 2
    while (directory / f"{slug}.md").exists():
        slug = f"{base_slug}-{n}"
        n += 1
    return slug


def save_document(filename: str, content_bytes: bytes, title: Optional[str] = None) -> dict:
    """Saves an uploaded file as a new Document (docs/db/document-module.md's
    Add flow): <slug>.<ext> (bytes unchanged) + <slug>.md sidecar. `title`,
    if given (e.g. a Telegram caption), becomes the Document's title;
    otherwise it's inferred from the filename. Not exposed as an MCP tool —
    file bytes can't reasonably flow through a tool-call's JSON arguments,
    so the caller (app/main.py) downloads the file and calls this directly,
    deterministically, without involving claude."""
    directory = docs_dir()
    directory.mkdir(parents=True, exist_ok=True)

    # ext ends up directly in a filesystem path below, and filename is
    # attacker/user-controlled (whatever the sender's Telegram client sends
    # as the original filename) — unlike slug (always slugify()'d), ext
    # needs its own explicit validation rather than just .lower(), or a
    # crafted filename could smuggle a "/" or ".." into the path.
    if "." in filename:
        stem, ext = filename.rsplit(".", 1)
        ext = ext.lower()
        if not VALID_EXT.match(ext):
            ext = "bin"
    else:
        stem, ext = filename, "bin"

    resolved_title = (
        title.strip() if title and title.strip()
        else stem.replace("_", " ").replace("-", " ").strip() or filename
    )

    base_slug = slugify(resolved_title)
    slug = _unique_slug(base_slug, directory)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    (directory / f"{slug}.{ext}").write_bytes(content_bytes)

    sidecar = "\n".join([
        "---",
        f"slug: {slug}",
        f"title: {resolved_title}",
        f"original_filename: {filename}",
        f"file_extension: {ext}",
        f"added_at: {now}",
        "---",
        "",
        f"Saved from a Telegram document upload: {resolved_title}.",
        "",
    ])
    (directory / f"{slug}.md").write_text(sidecar, encoding="utf-8")

    return {"slug": slug, "title": resolved_title, "original_filename": filename}

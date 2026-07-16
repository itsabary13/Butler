"""Metadata-only document lookup, reusing the sidecar format documented in
docs/db/document-module.md. Deliberately thin for v1 — no binary delivery
over voice (specs/epics/voice-relay.md's out-of-scope list); this only
tells the model what exists and when it was added.
"""

from pathlib import Path

from app.config import settings
from app.frontmatter import parse_page  # same flat frontmatter format


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

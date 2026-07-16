"""Shared flat key:value frontmatter parser, matching the format used by
backend/memory-module/tests/validate_wiki.py and
backend/document-module/tests/validate_documents.py — not a full YAML
parser, since the documented format (docs/db/memory-module.md,
docs/db/document-module.md) only ever uses flat scalar fields.
"""

from pathlib import Path
from typing import Optional


def parse_page(path: Path) -> tuple[Optional[dict], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fm_text = text[4:end]
    body = text[end + 4:].lstrip("\n")
    frontmatter = {}
    for line in fm_text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body

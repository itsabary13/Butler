"""Per-chat_id Claude Code session id (docs/db/voice-relay.md's Session
store), TTL-bounded. Multi-turn context itself is Claude Code's own
--resume mechanism (app/claude_code_client.py) — this table only remembers
which session id to resume, not conversation text, so a long-idle chat
starts fresh instead of resuming stale context.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.config import settings

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sessions.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            chat_id TEXT PRIMARY KEY,
            claude_session_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def get_session_id(chat_id: str) -> Optional[str]:
    """None if there's no session or it's past the TTL — either way the
    next call omits --resume and starts a fresh Claude Code session."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT claude_session_id, updated_at FROM sessions WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    claude_session_id, updated_at = row
    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - updated > timedelta(minutes=settings.session_ttl_minutes):
        return None
    return claude_session_id


def set_session_id(chat_id: str, claude_session_id: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO sessions (chat_id, claude_session_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                claude_session_id = excluded.claude_session_id,
                updated_at = excluded.updated_at
            """,
            (chat_id, claude_session_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

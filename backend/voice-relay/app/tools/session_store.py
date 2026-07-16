"""Short-term, per-chat_id conversation history (docs/db/voice-relay.md's
Session store). SQLite so a local dev restart doesn't wipe an
in-progress test conversation — losing this on restart in production is
still an accepted Phase 1 limitation, this just makes local iteration
less annoying.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sessions.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            chat_id TEXT PRIMARY KEY,
            history_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def get_history(chat_id: str) -> list[dict]:
    """Returns [] if there's no session or it's past the TTL — a fresh
    conversation starts either way, per voice-conversation.md's edge case."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT history_json, updated_at FROM sessions WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return []

    history_json, updated_at = row
    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - updated > timedelta(minutes=settings.session_ttl_minutes):
        return []
    return json.loads(history_json)


def append_turn(chat_id: str, role: str, text: str) -> None:
    history = get_history(chat_id)
    history.append({
        "role": role,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    history = history[-settings.session_max_turns:]

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO sessions (chat_id, history_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                history_json = excluded.history_json,
                updated_at = excluded.updated_at
            """,
            (chat_id, json.dumps(history), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

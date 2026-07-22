"""Proactive-notification dedup/audit log (docs/db/voice-relay.md's
Notification store, v1.6 addendum). Separate file from session_store.py's
sessions.db — that table is a TTL-ephemeral cache; this one is a durable
log an unattended daily scan writes proposals into and a Python gate reads
back before ever sending anything (app/proactive.py).
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "notifications.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key   TEXT NOT NULL,
            message     TEXT NOT NULL,
            status      TEXT NOT NULL,
            proposed_at TEXT NOT NULL,
            sent_at     TEXT
        )
        """
    )
    return conn


def record_proposal(dedup_key: str, message: str) -> None:
    """Called by the propose_notification MCP tool during an unattended
    proactive scan (app/claude_code_client.py's run_proactive_check) — this
    only ever records a candidate, it never sends anything. Status starts
    'proposed'; app/proactive.py's gate updates it to 'sent'/'deferred'/
    'suppressed' afterward."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO notifications (dedup_key, message, status, proposed_at) VALUES (?, ?, 'proposed', ?)",
            (dedup_key, message, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_proposals_since(run_start_iso: str) -> list[dict]:
    """Proposals from the run that just finished — the caller notes
    run_start before spawning claude, so the model never needs to pass a
    run id around itself."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, dedup_key, message FROM notifications WHERE proposed_at >= ? AND status = 'proposed' ORDER BY id",
            (run_start_iso,),
        ).fetchall()
    finally:
        conn.close()
    return [{"id": row[0], "dedup_key": row[1], "message": row[2]} for row in rows]


def was_recently_sent(dedup_key: str, cooldown_days: int) -> bool:
    """True if this dedup_key was already sent within the cooldown window —
    an appointment (keyed by its Calendar event id) naturally never re-fires
    once past; a fuzzy item (e.g. a checkup-due pattern) can legitimately
    re-surface after the cooldown if still unaddressed."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT sent_at FROM notifications WHERE dedup_key = ? AND status = 'sent' ORDER BY sent_at DESC LIMIT 1",
            (dedup_key,),
        ).fetchone()
    finally:
        conn.close()

    if row is None or row[0] is None:
        return False
    sent_at = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - sent_at < timedelta(days=cooldown_days)


def mark_status(row_id: int, status: str) -> None:
    conn = _connect()
    try:
        if status == "sent":
            conn.execute(
                "UPDATE notifications SET status = ?, sent_at = ? WHERE id = ?",
                (status, datetime.now(timezone.utc).isoformat(), row_id),
            )
        else:
            conn.execute("UPDATE notifications SET status = ? WHERE id = ?", (status, row_id))
        conn.commit()
    finally:
        conn.close()


def get_recent(days: int) -> list[dict]:
    """Every notification (any status) proposed in the last `days` days,
    most recent first — fed into the proactive scan's own prompt
    (app/claude_code_client.py's run_proactive_check) so the model can
    reuse the SAME dedup_key for something it already flagged, rather than
    inventing a new one each run. Without this, a fuzzy/wiki-derived item
    (no natural stable id, unlike a Calendar event) would drift to a
    different key every day — a run has no memory of a prior run's own
    keys otherwise, since it's a fresh, non-resumed claude invocation —
    which would silently defeat was_recently_sent's dedup entirely."""
    conn = _connect()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT dedup_key, message, status, proposed_at FROM notifications WHERE proposed_at >= ? ORDER BY proposed_at DESC",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    return [{"dedup_key": r[0], "message": r[1], "status": r[2], "proposed_at": r[3]} for r in rows]


def sent_count_last_24h() -> int:
    conn = _connect()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        row = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE status = 'sent' AND sent_at >= ?",
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    return row[0]

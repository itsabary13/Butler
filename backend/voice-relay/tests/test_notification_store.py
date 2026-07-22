from datetime import datetime, timedelta, timezone

import pytest

from app.tools import notification_store

EPOCH = "2020-01-01T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(notification_store, "DB_PATH", tmp_path / "notifications.db")


def test_record_and_get_proposals_since():
    notification_store.record_proposal("event-1", "You have an appointment tomorrow.")

    proposals = notification_store.get_proposals_since(EPOCH)

    assert len(proposals) == 1
    assert proposals[0]["dedup_key"] == "event-1"
    assert proposals[0]["message"] == "You have an appointment tomorrow."


def test_get_proposals_since_excludes_earlier_proposals():
    notification_store.record_proposal("event-1", "old")
    cutoff = datetime.now(timezone.utc).isoformat()
    notification_store.record_proposal("event-2", "new")

    proposals = notification_store.get_proposals_since(cutoff)

    assert [p["dedup_key"] for p in proposals] == ["event-2"]


def test_get_proposals_since_excludes_already_processed_proposals():
    notification_store.record_proposal("event-1", "msg")
    proposals = notification_store.get_proposals_since(EPOCH)
    notification_store.mark_status(proposals[0]["id"], "sent")

    # a re-query for the same window should no longer surface the
    # already-actioned (no longer 'proposed') row
    assert notification_store.get_proposals_since(EPOCH) == []


def test_was_recently_sent_false_when_never_sent():
    assert notification_store.was_recently_sent("event-1", cooldown_days=30) is False


def test_was_recently_sent_true_within_cooldown():
    notification_store.record_proposal("event-1", "msg")
    proposals = notification_store.get_proposals_since(EPOCH)
    notification_store.mark_status(proposals[0]["id"], "sent")

    assert notification_store.was_recently_sent("event-1", cooldown_days=30) is True


def test_was_recently_sent_false_after_cooldown_elapsed():
    notification_store.record_proposal("event-1", "msg")
    proposals = notification_store.get_proposals_since(EPOCH)
    row_id = proposals[0]["id"]

    conn = notification_store._connect()
    old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    conn.execute("UPDATE notifications SET status='sent', sent_at=? WHERE id=?", (old, row_id))
    conn.commit()
    conn.close()

    assert notification_store.was_recently_sent("event-1", cooldown_days=30) is False


def test_deferred_and_suppressed_do_not_count_as_sent():
    notification_store.record_proposal("event-1", "msg")
    proposals = notification_store.get_proposals_since(EPOCH)
    notification_store.mark_status(proposals[0]["id"], "deferred")

    assert notification_store.was_recently_sent("event-1", cooldown_days=30) is False
    assert notification_store.sent_count_last_24h() == 0


def test_get_recent_includes_any_status_most_recent_first():
    notification_store.record_proposal("older", "first")
    proposals = notification_store.get_proposals_since(EPOCH)
    notification_store.mark_status(proposals[0]["id"], "sent")
    notification_store.record_proposal("newer", "second")

    recent = notification_store.get_recent(days=30)

    assert [r["dedup_key"] for r in recent] == ["newer", "older"]
    assert recent[1]["status"] == "sent"


def test_get_recent_excludes_entries_outside_the_window():
    notification_store.record_proposal("old-thing", "msg")
    row_id = notification_store.get_proposals_since(EPOCH)[0]["id"]

    conn = notification_store._connect()
    old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    conn.execute("UPDATE notifications SET proposed_at = ? WHERE id = ?", (old, row_id))
    conn.commit()
    conn.close()

    assert notification_store.get_recent(days=30) == []


def test_get_recent_empty_when_nothing_proposed():
    assert notification_store.get_recent(days=30) == []


def test_sent_count_last_24h_only_counts_recent_sends():
    notification_store.record_proposal("a", "msg")
    proposals = notification_store.get_proposals_since(EPOCH)
    notification_store.mark_status(proposals[0]["id"], "sent")

    assert notification_store.sent_count_last_24h() == 1

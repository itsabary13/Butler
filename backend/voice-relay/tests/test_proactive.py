"""Tests app/proactive.py's gating logic — the deterministic chokepoint
between the model's proposals (which never send anything themselves) and
an actual Telegram send. Mocks claude_code_client.run_proactive_check and
telegram.send_text_reply; never invokes a real claude subprocess or makes
a real network call."""

import asyncio
from datetime import datetime, timezone

import pytest

from app import proactive
from app.tools import notification_store


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(notification_store, "DB_PATH", tmp_path / "notifications.db")
    monkeypatch.setattr(proactive.wiki_sync, "sync_before", lambda repo_dir: None)


def _enable(monkeypatch, **overrides):
    monkeypatch.setattr(proactive.settings, "proactive_enabled", True)
    monkeypatch.setattr(proactive.settings, "proactive_max_per_day", overrides.get("max_per_day", 3))
    monkeypatch.setattr(proactive.settings, "proactive_cooldown_days", overrides.get("cooldown_days", 30))
    monkeypatch.setattr(proactive.settings, "quiet_hours_start", overrides.get("quiet_start", 0))
    monkeypatch.setattr(proactive.settings, "quiet_hours_end", overrides.get("quiet_end", 24))
    monkeypatch.setattr(proactive.settings, "local_timezone", "UTC")


def _run(coro):
    return asyncio.run(coro)


def _async_recorder(sink):
    """Returns an async stand-in for telegram.send_text_reply that records
    the message text — used even where a test expects zero sends, so a
    future logic bug that DOES reach the send call fails loudly (a
    TypeError on awaiting a non-coroutine) instead of silently."""
    async def _send(chat_id, text):
        sink.append(text)
    return _send


def test_disabled_does_nothing(monkeypatch):
    monkeypatch.setattr(proactive.settings, "proactive_enabled", False)
    calls = []
    monkeypatch.setattr(proactive.claude_code_client, "run_proactive_check", lambda: calls.append(True))

    _run(proactive.run_daily_scan())

    assert calls == []


def test_sends_a_proposal_and_marks_it_sent(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(
        proactive.claude_code_client, "run_proactive_check",
        lambda: notification_store.record_proposal("event-1", "You have a dentist appointment tomorrow."),
    )
    sent = []
    monkeypatch.setattr(proactive.telegram, "send_text_reply", _async_recorder(sent))
    monkeypatch.setattr(proactive.settings, "telegram_owner_chat_id", "12345")

    _run(proactive.run_daily_scan())

    assert sent == ["You have a dentist appointment tomorrow."]
    assert notification_store.was_recently_sent("event-1", cooldown_days=30) is True


def test_no_proposals_sends_nothing(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(proactive.claude_code_client, "run_proactive_check", lambda: "no action items today.")
    sent = []
    monkeypatch.setattr(proactive.telegram, "send_text_reply", _async_recorder(sent))

    _run(proactive.run_daily_scan())

    assert sent == []


def test_suppresses_a_dedup_key_sent_within_cooldown(monkeypatch):
    _enable(monkeypatch, cooldown_days=30)
    notification_store.record_proposal("event-1", "earlier")
    proposals = notification_store.get_proposals_since("2020-01-01T00:00:00+00:00")
    notification_store.mark_status(proposals[0]["id"], "sent")

    monkeypatch.setattr(
        proactive.claude_code_client, "run_proactive_check",
        lambda: notification_store.record_proposal("event-1", "same appointment, proposed again"),
    )
    sent = []
    monkeypatch.setattr(proactive.telegram, "send_text_reply", _async_recorder(sent))

    _run(proactive.run_daily_scan())

    assert sent == []


def test_stops_at_daily_cap(monkeypatch):
    _enable(monkeypatch, max_per_day=1)
    monkeypatch.setattr(proactive.settings, "telegram_owner_chat_id", "12345")

    def fake_check():
        notification_store.record_proposal("a", "first")
        notification_store.record_proposal("b", "second")

    monkeypatch.setattr(proactive.claude_code_client, "run_proactive_check", fake_check)
    sent = []
    monkeypatch.setattr(proactive.telegram, "send_text_reply", _async_recorder(sent))

    _run(proactive.run_daily_scan())

    assert sent == ["first"]


def test_defers_everything_outside_quiet_hours(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(proactive, "_within_quiet_hours", lambda: False)

    monkeypatch.setattr(
        proactive.claude_code_client, "run_proactive_check",
        lambda: notification_store.record_proposal("event-1", "msg"),
    )
    sent = []
    monkeypatch.setattr(proactive.telegram, "send_text_reply", _async_recorder(sent))

    _run(proactive.run_daily_scan())

    assert sent == []


def test_within_quiet_hours_normal_window(monkeypatch):
    monkeypatch.setattr(proactive.settings, "quiet_hours_start", 8)
    monkeypatch.setattr(proactive.settings, "quiet_hours_end", 21)
    monkeypatch.setattr(proactive, "_local_now", lambda: datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))

    assert proactive._within_quiet_hours() is True


def test_within_quiet_hours_outside_normal_window(monkeypatch):
    monkeypatch.setattr(proactive.settings, "quiet_hours_start", 8)
    monkeypatch.setattr(proactive.settings, "quiet_hours_end", 21)
    monkeypatch.setattr(proactive, "_local_now", lambda: datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))

    assert proactive._within_quiet_hours() is False


def test_within_quiet_hours_wraps_past_midnight(monkeypatch):
    monkeypatch.setattr(proactive.settings, "quiet_hours_start", 22)
    monkeypatch.setattr(proactive.settings, "quiet_hours_end", 6)
    monkeypatch.setattr(proactive, "_local_now", lambda: datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc))

    assert proactive._within_quiet_hours() is True


def test_claude_failure_does_not_raise(monkeypatch):
    _enable(monkeypatch)

    def fake_check():
        raise RuntimeError("boom")

    monkeypatch.setattr(proactive.claude_code_client, "run_proactive_check", fake_check)

    _run(proactive.run_daily_scan())  # must not raise

"""Tests app/config.py's local_now() — shared by app/proactive.py's
scheduling/quiet-hours math and app/claude_code_client.py's system prompt
(v1.9 fix). No live provider calls, matching this suite's existing rule."""

from datetime import timezone

from app.config import local_now, settings


def test_local_now_uses_configured_timezone(monkeypatch):
    monkeypatch.setattr(settings, "local_timezone", "Asia/Jerusalem")

    result = local_now()

    assert str(result.tzinfo) == "Asia/Jerusalem"


def test_local_now_falls_back_to_utc_for_invalid_timezone(monkeypatch):
    monkeypatch.setattr(settings, "local_timezone", "Not/A_Real_Zone")

    result = local_now()

    assert result.tzinfo == timezone.utc

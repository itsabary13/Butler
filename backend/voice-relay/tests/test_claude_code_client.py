"""Tests app/claude_code_client.py's subprocess invocation and JSON-result
parsing against a mocked `claude` process — never shells out to a real
`claude` binary (that only happens in real live-verification, Task 43)."""

import json

import pytest

from app import claude_code_client
from app.tools import session_store


class _FakeCompletedProcess:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


@pytest.fixture(autouse=True)
def _isolated_session_db(monkeypatch, tmp_path):
    monkeypatch.setattr(session_store, "DB_PATH", tmp_path / "sessions.db")


def test_get_reply_returns_result_and_stores_session_id(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _FakeCompletedProcess(json.dumps({"result": "Got it.", "session_id": "sess-1"}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    reply = claude_code_client.get_reply("12345", "remind me to call mom every Sunday")

    assert reply == "Got it."
    assert "--resume" not in captured["command"]
    assert session_store.get_session_id("12345") == "sess-1"


def test_get_reply_resumes_an_existing_session(monkeypatch):
    session_store.set_session_id("12345", "sess-1")

    def fake_run(command, **kwargs):
        assert command[command.index("--resume") + 1] == "sess-1"
        return _FakeCompletedProcess(json.dumps({"result": "Sure.", "session_id": "sess-1"}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    claude_code_client.get_reply("12345", "and remind me tomorrow too")


def test_get_reply_raises_on_nonzero_exit(monkeypatch):
    def fake_run(command, **kwargs):
        return _FakeCompletedProcess("", returncode=1, stderr="boom")

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    with pytest.raises(claude_code_client.ClaudeCodeError):
        claude_code_client.get_reply("12345", "hello")


def test_get_reply_raises_when_result_missing(monkeypatch):
    def fake_run(command, **kwargs):
        return _FakeCompletedProcess(json.dumps({"session_id": "sess-1"}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    with pytest.raises(claude_code_client.ClaudeCodeError):
        claude_code_client.get_reply("12345", "hello")


def test_get_reply_falls_back_to_fresh_session_when_resume_fails(monkeypatch):
    # A stored session id can go stale (e.g. a redeploy wipes Claude Code's
    # own session storage) even within our TTL — should retry fresh, not fail.
    session_store.set_session_id("12345", "stale-session")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if "--resume" in command:
            return _FakeCompletedProcess("", returncode=1, stderr="No conversation found with session ID: stale-session")
        return _FakeCompletedProcess(json.dumps({"result": "Sure.", "session_id": "new-session"}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    reply = claude_code_client.get_reply("12345", "hello again")

    assert reply == "Sure."
    assert len(calls) == 2
    assert "--resume" in calls[0]
    assert "--resume" not in calls[1]
    assert session_store.get_session_id("12345") == "new-session"


def test_get_reply_raises_when_fresh_retry_also_fails(monkeypatch):
    session_store.set_session_id("12345", "stale-session")

    def fake_run(command, **kwargs):
        return _FakeCompletedProcess("", returncode=1, stderr="boom")

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    with pytest.raises(claude_code_client.ClaudeCodeError):
        claude_code_client.get_reply("12345", "hello")

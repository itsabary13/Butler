"""Tests app/claude_code_client.py's subprocess invocation and JSON-result
parsing against a mocked `claude` process — never shells out to a real
`claude` binary (that only happens in real live-verification, Task 43)."""

import json
from pathlib import Path

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


def test_enrich_document_scopes_read_to_the_files_own_directory(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _FakeCompletedProcess(json.dumps({"result": "Saved as Habima Theater Tickets."}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    file_path = Path("/data/docs/photo.jpg")
    summary = claude_code_client.enrich_document(file_path, "photo", "photo", "my theater tickets")

    assert summary == "Saved as Habima Theater Tickets."
    command = captured["command"]
    assert "--resume" not in command  # not a chat turn
    assert command[command.index("--add-dir") + 1] == str(file_path.parent)
    allowed_tools = command[command.index("--allowedTools") + 1]
    assert "Read" in allowed_tools
    assert "mcp__butler__categorize_document" in allowed_tools
    assert "mcp__butler__create_calendar_event" not in allowed_tools  # narrower than the conversational allowlist


def test_enrich_document_falls_back_to_generic_message_on_failure(monkeypatch):
    def fake_run(command, **kwargs):
        return _FakeCompletedProcess("", returncode=1, stderr="claude crashed")

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    summary = claude_code_client.enrich_document(Path("/data/docs/x.pdf"), "x", "x", None)

    assert "couldn't read" in summary.lower()


def test_proactive_allowed_tools_has_no_send_capable_or_filesystem_tool():
    # The daily scan can read wiki/calendar and propose a notification —
    # nothing else. In particular: no Read/Bash (unlike enrich_document,
    # this pass has no file to view), and no tool that could send anything
    # (save_memory/append_reminder/create_calendar_event all mutate state;
    # propose_notification only records a candidate, app/proactive.py's
    # gate owns the actual Telegram send).
    assert "Read" not in claude_code_client.PROACTIVE_ALLOWED_TOOLS
    assert "Bash" not in claude_code_client.PROACTIVE_ALLOWED_TOOLS
    for disallowed in ("save_memory", "append_reminder", "create_calendar_event"):
        assert not any(disallowed in tool for tool in claude_code_client.PROACTIVE_ALLOWED_TOOLS)
    assert "mcp__butler__propose_notification" in claude_code_client.PROACTIVE_ALLOWED_TOOLS


def test_run_proactive_check_uses_proactive_allowlist_and_no_resume(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _FakeCompletedProcess(json.dumps({"result": "no action items today."}))

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    summary = claude_code_client.run_proactive_check()

    assert summary == "no action items today."
    command = captured["command"]
    assert "--resume" not in command
    assert "--add-dir" not in command  # no file to scope Read to — it has no Read at all
    allowed_tools = command[command.index("--allowedTools") + 1]
    assert allowed_tools == ",".join(claude_code_client.PROACTIVE_ALLOWED_TOOLS)


def test_run_proactive_check_falls_back_to_message_on_failure(monkeypatch):
    def fake_run(command, **kwargs):
        return _FakeCompletedProcess("", returncode=1, stderr="claude crashed")

    monkeypatch.setattr(claude_code_client.subprocess, "run", fake_run)

    summary = claude_code_client.run_proactive_check()

    assert "scan failed" in summary.lower()

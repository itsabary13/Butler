"""The relay's 'brain' — headless Claude Code (`claude -p`), authenticated
via the user's Claude Pro/Max subscription (CLAUDE_CODE_OAUTH_TOKEN) instead
of a pay-per-token Anthropic API key. Replaces the earlier direct Anthropic
Messages API tool-use loop; see docs/architecture/voice-relay.md's v2
addendum for the full reasoning.

Tools (wiki/calendar/document access) are exposed over MCP
(app/mcp_server.py, mcp-config.json) rather than Anthropic tool-use
schemas — same app/tools/* implementations, different transport.
--allowed-tools is an explicit allowlist of only those 5 tools, so the
headless process has no Bash/file access beyond them (least privilege,
same spirit as the webhook's own hard chat_id allowlist).

Multi-turn context uses Claude Code's own --resume <session_id> instead of
manually replaying a transcript — app/tools/session_store.py stores just
the session id per chat_id (TTL-bounded), not conversation text. Claude
Code's own turn/tool-call budgeting replaces the old manual
MAX_TOOL_ROUNDS/MAX_WIKI_LINK_HOPS bookkeeping.
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.tools import session_store, wiki_tools

logger = logging.getLogger("voice_relay.claude_code_client")

VOICE_RELAY_DIR = Path(__file__).resolve().parent.parent
MCP_CONFIG_PATH = VOICE_RELAY_DIR / "mcp-config.json"

ALLOWED_TOOLS = [
    "mcp__butler__read_wiki_page",
    "mcp__butler__save_memory",
    "mcp__butler__append_reminder",
    "mcp__butler__create_calendar_event",
    "mcp__butler__find_document",
]

CLAUDE_TIMEOUT_SECONDS = 60


class ClaudeCodeError(RuntimeError):
    """Raised when the headless `claude` process fails or returns no usable result."""


def _system_prompt() -> str:
    manifest = wiki_tools.list_wiki_pages()
    manifest_lines = "\n".join(
        f"- {p['slug']} ({p['title']}){' [' + p['tag'] + ']' if p['tag'] else ''}"
        for p in manifest
    ) or "(no memories saved yet)"

    now = datetime.now(timezone.utc).isoformat()

    return f"""You are Butler, a calm, concise, helpful voice assistant. You are answering a
voice message that was transcribed to text — keep replies short and natural to
speak aloud, not a long written answer.

Current time (UTC): {now}

Memory wiki manifest (topics you know something about — read a page with
read_wiki_page before claiming to know its details; never fabricate a memory
that isn't actually in the wiki):
{manifest_lines}

Rules:
- Never fabricate a memory, reminder, or document that doesn't actually exist.
- Only call create_calendar_event once the date/time is unambiguous; ask instead of guessing.
- create_calendar_event is create-only — there is no update/delete tool. If asked to change or
  cancel an existing event, say that isn't supported yet.
- Only call save_memory/append_reminder for things clearly worth remembering long-term, not
  every detail of the conversation.
- Confirm what you actually did in your reply (e.g. state the event time you created), not a
  generic acknowledgment.
"""


def get_reply(chat_id: str, user_text: str) -> str:
    resume_id = session_store.get_session_id(chat_id)

    command = [
        settings.claude_binary,
        "-p", user_text,
        "--output-format", "json",
        "--append-system-prompt", _system_prompt(),
        "--mcp-config", str(MCP_CONFIG_PATH),
        "--allowedTools", ",".join(ALLOWED_TOOLS),
    ]
    if settings.claude_code_model:
        command += ["--model", settings.claude_code_model]
    if resume_id:
        command += ["--resume", resume_id]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
            cwd=VOICE_RELAY_DIR,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClaudeCodeError(f"claude timed out after {CLAUDE_TIMEOUT_SECONDS}s") from exc

    if result.returncode != 0:
        logger.error("claude exited %s: %s", result.returncode, result.stderr[-2000:])
        raise ClaudeCodeError(f"claude exited {result.returncode}: {result.stderr[-500:]}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ClaudeCodeError(f"claude returned non-JSON output: {result.stdout[-500:]}") from exc

    reply_text = payload.get("result")
    new_session_id = payload.get("session_id")
    if not reply_text:
        raise ClaudeCodeError(f"claude returned no result: {payload}")

    if new_session_id:
        session_store.set_session_id(chat_id, new_session_id)

    return reply_text.strip()

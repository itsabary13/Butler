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

# For the document-enrichment pass only (enrich_document below) — narrower
# than ALLOWED_TOOLS (no calendar/reminders/find_document, none of which
# this pass needs) but adds Read, which the conversational path
# deliberately never gets. Read access is scoped via --add-dir to just the
# docs directory (enrich_document's caller), not granted repo-wide.
DOCUMENT_ALLOWED_TOOLS = [
    "Read",
    "mcp__butler__categorize_document",
    "mcp__butler__save_memory",
]

CLAUDE_TIMEOUT_SECONDS = 60
DOCUMENT_TIMEOUT_SECONDS = 90  # reading/describing a file's actual content can run longer than a plain reply


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


def _build_command(user_text: str, resume_id: str | None) -> list[str]:
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
    return command


def _run_claude(command: list[str], timeout: int = CLAUDE_TIMEOUT_SECONDS) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=VOICE_RELAY_DIR,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClaudeCodeError(f"claude timed out after {timeout}s") from exc

    if result.returncode != 0:
        logger.error("claude exited %s: %s", result.returncode, result.stderr[-2000:])
        raise ClaudeCodeError(f"claude exited {result.returncode}: {result.stderr[-500:]}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ClaudeCodeError(f"claude returned non-JSON output: {result.stdout[-500:]}") from exc


def get_reply(chat_id: str, user_text: str) -> str:
    resume_id = session_store.get_session_id(chat_id)

    try:
        payload = _run_claude(_build_command(user_text, resume_id))
    except ClaudeCodeError:
        if resume_id is None:
            raise
        # A stored session id can go stale even within our own TTL — e.g. a
        # redeploy wipes Claude Code's own session storage. Fall back to a
        # fresh session once rather than failing the whole turn.
        logger.warning("resume failed for chat_id=%s (session_id=%s), retrying fresh", chat_id, resume_id)
        payload = _run_claude(_build_command(user_text, resume_id=None))

    reply_text = payload.get("result")
    new_session_id = payload.get("session_id")
    if not reply_text:
        raise ClaudeCodeError(f"claude returned no result: {payload}")

    if new_session_id:
        session_store.set_session_id(chat_id, new_session_id)

    return reply_text.strip()


def enrich_document(file_path: Path, slug: str, initial_title: str, caption: str | None) -> str:
    """Reads an uploaded document/photo's actual content and (a) renames/
    categorizes it via categorize_document, replacing the placeholder title
    save_document started with, and (b) saves anything worth remembering
    via save_memory, so it's answerable by content later (recall), not just
    findable by title substring (find_document). v1.5 addendum,
    docs/architecture/voice-relay.md.

    A separate, narrower invocation from get_reply's conversational one:
    no --resume (this isn't a chat turn — the wiki itself, not session
    state, is what makes the content askable later), and a tighter
    --allowedTools that adds Read (needed to view the file at all) scoped
    via --add-dir to just file_path's own directory.
    """
    caption_line = f'The uploader captioned it: "{caption}"' if caption else "No caption was given."

    prompt = f"""A file was just uploaded and saved at {file_path} (current placeholder slug: "{slug}", title: "{initial_title}").
{caption_line}

Read it (or view it, if it's an image), then:
1. Call categorize_document with a short, specific, content-derived title and
   a one-or-two-word category (e.g. "ticket", "receipt", "ID", "invoice",
   "letter", "photo", "screenshot" — pick whatever actually fits, don't force
   one of these if none fit; omit category if genuinely nothing fits).
2. If there's genuinely something worth remembering about its content (key
   facts, dates, names, visible text), call save_memory too, under a new
   sensible slug — so it's answerable later ("what does my X say"), not just
   findable by title.

If the file can't be meaningfully read (corrupt, unsupported, blank), call
categorize_document with a best-effort generic title/category instead of
inventing content, and skip save_memory.

Reply with one short sentence summarizing what you did."""

    command = [
        settings.claude_binary,
        "-p", prompt,
        "--output-format", "json",
        "--add-dir", str(file_path.parent),
        "--mcp-config", str(MCP_CONFIG_PATH),
        "--allowedTools", ",".join(DOCUMENT_ALLOWED_TOOLS),
    ]
    if settings.claude_code_model:
        command += ["--model", settings.claude_code_model]

    try:
        payload = _run_claude(command, timeout=DOCUMENT_TIMEOUT_SECONDS)
    except ClaudeCodeError as exc:
        logger.warning("document enrichment failed for %s: %s", file_path, exc)
        return "Saved with the basic title only — couldn't read its content automatically."

    return (payload.get("result") or "").strip() or "Saved."

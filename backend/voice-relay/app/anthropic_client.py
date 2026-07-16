"""The relay's 'brain' — a direct Anthropic API tool-use loop standing in
for what a Claude Code session + skills would normally do
(docs/architecture/voice-relay.md explains why skills/routines can't be
used directly here).

Context assembly mirrors recall's steps: a cheap manifest (no bodies) up
front, then explicit read_wiki_page tool calls for whatever looks
relevant, following [[wiki-link]] references the same way. Wiki-link
hops are capped per turn to bound latency (docs/architecture's risk
note).
"""

import logging
from datetime import datetime, timezone

import anthropic

from app.config import settings
from app.tools import calendar_tools, document_tools, wiki_tools

logger = logging.getLogger("voice_relay.anthropic_client")

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MAX_WIKI_LINK_HOPS = 4
MAX_TOOL_ROUNDS = 8  # hard ceiling regardless of hop counting, so a loop bug can't run away

TOOLS = [
    {
        "name": "read_wiki_page",
        "description": "Read the full content of one memory wiki page by slug, including any [[wiki-link]] references to other pages.",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "save_memory",
        "description": "Save a new fact, or merge new information into an existing page if one already covers the same topic. Use an existing slug from the wiki manifest to merge, or a new kebab-case slug to create a page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tag": {"type": "string", "enum": ["private", "work"], "description": "Only set when creating a new page and the topic clearly reads as private or work. Omit otherwise."},
            },
            "required": ["slug", "title", "content"],
        },
    },
    {
        "name": "append_reminder",
        "description": "Record a date/recurrence-triggered action item (e.g. 'every 10th' or a specific date) the user needs to do. Only use when the message clearly has BOTH a date/recurrence AND an action needed — most facts are not reminders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule": {"type": "string", "description": "e.g. 'every 10th', 'every Monday', or a specific date like '2026-09-01'"},
                "description": {"type": "string"},
            },
            "required": ["rule", "description"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a real event on the user's Google Calendar. Only call this once the date/time is unambiguous — ask a clarifying question in your text response instead of calling this if it's vague.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_iso": {"type": "string", "description": "ISO 8601 datetime, or date (YYYY-MM-DD) if all_day"},
                "end_iso": {"type": "string"},
                "all_day": {"type": "boolean", "default": False},
                "recurrence_rule": {"type": "string", "description": "RFC 5545 RRULE string, e.g. RRULE:FREQ=MONTHLY;BYMONTHDAY=10. Omit for a one-off event."},
            },
            "required": ["summary", "start_iso", "end_iso"],
        },
    },
    {
        "name": "find_document",
        "description": "Look up stored documents by title/filename (metadata only — you cannot read or deliver the actual file content over voice).",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

_TOOL_DISPATCH = {
    "read_wiki_page": lambda **kw: wiki_tools.read_wiki_page(**kw),
    "save_memory": lambda **kw: wiki_tools.save_memory(**kw),
    "append_reminder": lambda **kw: wiki_tools.append_reminder(**kw),
    "create_calendar_event": lambda **kw: calendar_tools.create_calendar_event(**kw),
    "find_document": lambda **kw: document_tools.find_document(**kw),
}


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


def get_reply(user_text: str, history: list[dict]) -> str:
    messages = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})
    messages.append({"role": "user", "content": user_text})

    tool_rounds = 0
    wiki_hops = 0

    while True:
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

        tool_rounds += 1
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "read_wiki_page":
                wiki_hops += 1

            over_limit = wiki_hops > MAX_WIKI_LINK_HOPS or tool_rounds > MAX_TOOL_ROUNDS
            if over_limit:
                result = {"error": "tool call budget exceeded for this turn — answer with what you already know"}
            else:
                try:
                    result = _TOOL_DISPATCH[block.name](**block.input)
                except Exception as exc:  # noqa: BLE001 — surfaced to the model, not swallowed silently
                    logger.exception("tool %s failed", block.name)
                    result = {"error": str(exc)}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _to_tool_content(result),
            })

        messages.append({"role": "user", "content": tool_results})


def _to_tool_content(result) -> str:
    import json
    return json.dumps(result, default=str)

"""Local stdio MCP server exposing the relay's wiki/calendar/document tools
to the headless `claude` process (app/claude_code_client.py). Registered via
mcp-config.json, run as `python -m app.mcp_server`.

Only wraps app/tools/* — the security-reviewed implementations (slug path
traversal guard, create/list-only calendar, metadata-only document lookup)
are unchanged; this file just re-exposes them over MCP instead of the
Anthropic tool-use schema the direct-API loop used to send.
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from app.tools import calendar_tools, document_tools, notification_store, wiki_tools

mcp = FastMCP("butler")


@mcp.tool()
def read_wiki_page(slug: str) -> dict:
    """Read the full content of one memory wiki page by slug, including any [[wiki-link]] references to other pages."""
    return wiki_tools.read_wiki_page(slug) or {"error": "not found"}


@mcp.tool()
def save_memory(slug: str, title: str, content: str, tag: Optional[str] = None) -> dict:
    """Save a new fact, or merge new information into an existing page if one already covers the same topic. Use an existing slug from the wiki manifest to merge, or a new kebab-case slug to create a page. Only set tag when creating a new page and the topic clearly reads as private or work."""
    return wiki_tools.save_memory(slug, title, content, tag)


@mcp.tool()
def append_reminder(rule: str, description: str) -> dict:
    """Record a date/recurrence-triggered action item (e.g. 'every 10th' or a specific date) the user needs to do. Only use when the message clearly has BOTH a date/recurrence AND an action needed."""
    return wiki_tools.append_reminder(rule, description)


@mcp.tool()
def create_calendar_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    all_day: bool = False,
    recurrence_rule: Optional[str] = None,
) -> dict:
    """Create a real event on the user's Google Calendar. Only call this once the date/time is unambiguous — ask a clarifying question instead of calling this if it's vague."""
    return calendar_tools.create_calendar_event(summary, start_iso, end_iso, all_day, recurrence_rule)


@mcp.tool()
def find_document(query: str) -> list:
    """Look up stored documents by title/filename/category (metadata only — you cannot read or deliver the actual file content over voice)."""
    return document_tools.find_document(query)


@mcp.tool()
def categorize_document(slug: str, title: str, category: Optional[str] = None) -> dict:
    """Finalize a just-uploaded document's title and category after reading its actual content. Only usable on a document that already exists (by slug) — this renames/relabels it, it does not create a new one. title should be short and specific to what the document actually is; category should be a short word or two (e.g. "ticket", "receipt", "ID", "invoice", "photo") or omitted if nothing fits."""
    return document_tools.categorize_document(slug, title, category)


@mcp.tool()
def list_upcoming_events(days_ahead: int = 7) -> list:
    """List the user's real Google Calendar events between now and days_ahead from now (read-only)."""
    return calendar_tools.list_upcoming_events(days_ahead)


@mcp.tool()
def propose_notification(dedup_key: str, message: str) -> dict:
    """Propose an unprompted notification to send the user later — this does NOT send anything itself, it only records a candidate for a separate process to review. Only call this during a proactive scan, and only for something genuinely worth an unprompted interruption (an imminent appointment, a clearly overdue recurring item) — not for routine information. dedup_key must be stable across runs for the same underlying thing (a Calendar event's own id for an appointment; a short descriptive slug like "annual-checkup-due" for a recurring/fuzzy item) so the same item is never proposed as if new every time it's still true. message should be short and natural, ready to send as-is."""
    notification_store.record_proposal(dedup_key, message)
    return {"status": "proposed"}


if __name__ == "__main__":
    mcp.run(transport="stdio")

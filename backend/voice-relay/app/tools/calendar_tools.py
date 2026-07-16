"""Direct Google Calendar API access — NOT via Claude Code's Calendar
connector, since this is a separate OS process with no access to that
connector. Own OAuth credentials, own token refresh.

Create-only for v1 (specs/stories/voice-relay/voice-calendar-action.md) —
matches Memory's own precedent of deferring update/delete rather than
building it speculatively.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings


def _calendar_client():
    creds = Credentials(
        None,
        refresh_token=settings.google_oauth_refresh_token,
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    all_day: bool = False,
    recurrence_rule: str | None = None,
) -> dict:
    """start_iso/end_iso: ISO 8601 datetime (or date, if all_day) strings,
    already resolved to a concrete value by the caller — this tool never
    guesses an ambiguous time itself (FR-4, voice-calendar-action.md)."""
    body: dict = {"summary": summary}
    if all_day:
        body["start"] = {"date": start_iso}
        body["end"] = {"date": end_iso}
    else:
        body["start"] = {"dateTime": start_iso}
        body["end"] = {"dateTime": end_iso}
    if recurrence_rule:
        body["recurrence"] = [recurrence_rule]

    service = _calendar_client()
    created = service.events().insert(
        calendarId=settings.primary_calendar_id,
        body=body,
    ).execute()
    return {
        "id": created.get("id"),
        "summary": created.get("summary"),
        "start": created.get("start"),
        "htmlLink": created.get("htmlLink"),
    }

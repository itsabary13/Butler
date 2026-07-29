"""Direct Google Calendar API access — NOT via Claude Code's Calendar
connector, since this is a separate OS process with no access to that
connector. Own OAuth credentials, own token refresh.

list_upcoming_events (v1.6 addendum) is read-only, added for the
proactive-notification scan (app/proactive.py). update_calendar_event/
delete_calendar_event (v1.8 addendum) round out create+list into full
CRUD — deferred from earlier passes (specs/stories/voice-relay/
voice-calendar-action.md, matching Memory's own precedent of not building
update/delete speculatively) until there was an actual request for it.

v1.9 fix: create/update now always pass an explicit timeZone
(settings.local_timezone) alongside a timed dateTime — found live, this
was previously missing, so the Calendar API fell back to interpreting the
dateTime per the calendar's own default timezone rather than the user's,
silently creating/moving events at the wrong absolute time.
"""

from datetime import datetime, timedelta, timezone

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
    guesses an ambiguous time itself (FR-4, voice-calendar-action.md).

    A timed event always gets an explicit timeZone (settings.local_timezone)
    alongside dateTime — v1.9 fix: without it, a naive/offset-less dateTime
    string is ambiguous to the Calendar API (interpreted per the calendar's
    own default timezone, not necessarily the user's), which was silently
    creating events at the wrong absolute time."""
    body: dict = {"summary": summary}
    if all_day:
        body["start"] = {"date": start_iso}
        body["end"] = {"date": end_iso}
    else:
        body["start"] = {"dateTime": start_iso, "timeZone": settings.local_timezone}
        body["end"] = {"dateTime": end_iso, "timeZone": settings.local_timezone}
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


def list_upcoming_events(days_ahead: int = 7) -> list[dict]:
    """Events on the primary calendar between now and days_ahead from now —
    read-only, no update/delete capability added alongside this."""
    now = datetime.now(timezone.utc)
    service = _calendar_client()
    result = service.events().list(
        calendarId=settings.primary_calendar_id,
        timeMin=now.isoformat(),
        timeMax=(now + timedelta(days=days_ahead)).isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for event in result.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})
        events.append({
            "id": event.get("id"),
            "summary": event.get("summary"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "all_day": "date" in start,
        })
    return events


def update_calendar_event(
    event_id: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    all_day: bool | None = None,
    recurrence_rule: str | None = None,
) -> dict:
    """Partial update — only fields actually supplied are changed; a
    field left as None is left untouched on the existing event.
    event_id must come from a prior list_upcoming_events (or
    create_calendar_event's own return value) call, never guessed."""
    body: dict = {}
    if summary is not None:
        body["summary"] = summary
    if start_iso is not None:
        body["start"] = {"date": start_iso} if all_day else {"dateTime": start_iso, "timeZone": settings.local_timezone}
    if end_iso is not None:
        body["end"] = {"date": end_iso} if all_day else {"dateTime": end_iso, "timeZone": settings.local_timezone}
    if recurrence_rule is not None:
        body["recurrence"] = [recurrence_rule]

    service = _calendar_client()
    updated = service.events().patch(
        calendarId=settings.primary_calendar_id,
        eventId=event_id,
        body=body,
    ).execute()
    return {
        "id": updated.get("id"),
        "summary": updated.get("summary"),
        "start": updated.get("start"),
        "end": updated.get("end"),
        "htmlLink": updated.get("htmlLink"),
    }


def delete_calendar_event(event_id: str) -> dict:
    """Permanently removes the event — event_id must come from a prior
    list_upcoming_events call, never guessed. No undo."""
    service = _calendar_client()
    service.events().delete(
        calendarId=settings.primary_calendar_id,
        eventId=event_id,
    ).execute()
    return {"deleted": True, "id": event_id}

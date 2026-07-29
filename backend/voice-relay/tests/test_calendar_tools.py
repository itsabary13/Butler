"""Tests app/tools/calendar_tools.py against a fake Google Calendar API
client — never a real Google API call, matching test_email_tools.py's
established pattern. calendar_tools.py had zero test coverage before this
(flagged as a known gap in the v1.7 review) — closed here alongside the
new update/delete functions (v1.8 addendum)."""

from app.config import settings
from app.tools import calendar_tools


class _FakeExecutor:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeEvents:
    def __init__(self, insert_result=None, list_result=None, patch_result=None, delete_result=None):
        self.insert_result = insert_result
        self.list_result = list_result
        self.patch_result = patch_result
        self.delete_result = delete_result
        self.insert_calls = []
        self.list_calls = []
        self.patch_calls = []
        self.delete_calls = []

    def insert(self, calendarId, body):
        self.insert_calls.append({"calendarId": calendarId, "body": body})
        return _FakeExecutor(self.insert_result)

    def list(self, calendarId, timeMin, timeMax, singleEvents, orderBy):
        self.list_calls.append({
            "calendarId": calendarId, "timeMin": timeMin, "timeMax": timeMax,
            "singleEvents": singleEvents, "orderBy": orderBy,
        })
        return _FakeExecutor(self.list_result)

    def patch(self, calendarId, eventId, body):
        self.patch_calls.append({"calendarId": calendarId, "eventId": eventId, "body": body})
        return _FakeExecutor(self.patch_result)

    def delete(self, calendarId, eventId):
        self.delete_calls.append({"calendarId": calendarId, "eventId": eventId})
        return _FakeExecutor(self.delete_result)


class _FakeService:
    def __init__(self, events):
        self._events = events

    def events(self):
        return self._events


def test_create_calendar_event_timed(monkeypatch):
    events = _FakeEvents(insert_result={
        "id": "e1", "summary": "Dentist", "start": {"dateTime": "2026-08-01T10:00:00"}, "htmlLink": "https://cal/e1",
    })
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    result = calendar_tools.create_calendar_event("Dentist", "2026-08-01T10:00:00", "2026-08-01T11:00:00")

    assert events.insert_calls == [{
        "calendarId": settings.primary_calendar_id,
        "body": {
            "summary": "Dentist",
            "start": {"dateTime": "2026-08-01T10:00:00", "timeZone": settings.local_timezone},
            "end": {"dateTime": "2026-08-01T11:00:00", "timeZone": settings.local_timezone},
        },
    }]
    assert result == {"id": "e1", "summary": "Dentist", "start": {"dateTime": "2026-08-01T10:00:00"}, "htmlLink": "https://cal/e1"}


def test_create_calendar_event_uses_configured_local_timezone_not_a_hardcoded_default(monkeypatch):
    # v1.9 regression guard: a timed event with no explicit timeZone is
    # ambiguous to the Calendar API (interpreted per the calendar's own
    # default zone, not the user's) — this was silently creating events at
    # the wrong absolute time. Confirms the actual configured zone is used,
    # not a hardcoded "UTC" that would happen to match by coincidence.
    monkeypatch.setattr(settings, "local_timezone", "Asia/Jerusalem")
    events = _FakeEvents(insert_result={"id": "e1"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.create_calendar_event("Dentist", "2026-08-01T10:00:00", "2026-08-01T11:00:00")

    body = events.insert_calls[0]["body"]
    assert body["start"]["timeZone"] == "Asia/Jerusalem"
    assert body["end"]["timeZone"] == "Asia/Jerusalem"


def test_create_calendar_event_all_day_with_recurrence(monkeypatch):
    events = _FakeEvents(insert_result={"id": "e2", "summary": "Birthday", "start": {"date": "2026-08-01"}, "htmlLink": "https://cal/e2"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.create_calendar_event(
        "Birthday", "2026-08-01", "2026-08-02", all_day=True, recurrence_rule="RRULE:FREQ=YEARLY"
    )

    assert events.insert_calls[0]["body"] == {
        "summary": "Birthday", "start": {"date": "2026-08-01"}, "end": {"date": "2026-08-02"},
        "recurrence": ["RRULE:FREQ=YEARLY"],
    }


def test_list_upcoming_events_shapes_response(monkeypatch):
    events = _FakeEvents(list_result={"items": [
        {"id": "e1", "summary": "Dentist", "start": {"dateTime": "2026-08-01T10:00:00"}, "end": {"dateTime": "2026-08-01T11:00:00"}},
        {"id": "e2", "summary": "Birthday", "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}},
    ]})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    result = calendar_tools.list_upcoming_events(days_ahead=14)

    call = events.list_calls[0]
    assert call["calendarId"] == settings.primary_calendar_id
    assert call["singleEvents"] is True
    assert call["orderBy"] == "startTime"
    assert result == [
        {"id": "e1", "summary": "Dentist", "start": "2026-08-01T10:00:00", "end": "2026-08-01T11:00:00", "all_day": False},
        {"id": "e2", "summary": "Birthday", "start": "2026-08-05", "end": "2026-08-06", "all_day": True},
    ]


def test_list_upcoming_events_empty(monkeypatch):
    events = _FakeEvents(list_result={})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    assert calendar_tools.list_upcoming_events() == []


def test_update_calendar_event_only_includes_supplied_fields(monkeypatch):
    events = _FakeEvents(patch_result={"id": "e1", "summary": "New title", "start": None, "end": None, "htmlLink": "https://cal/e1"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.update_calendar_event("e1", summary="New title")

    assert events.patch_calls == [{"calendarId": settings.primary_calendar_id, "eventId": "e1", "body": {"summary": "New title"}}]


def test_update_calendar_event_timed_fields_use_datetime_keys(monkeypatch):
    events = _FakeEvents(patch_result={"id": "e1"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.update_calendar_event("e1", start_iso="2026-08-01T15:00:00", end_iso="2026-08-01T16:00:00")

    assert events.patch_calls[0]["body"] == {
        "start": {"dateTime": "2026-08-01T15:00:00", "timeZone": settings.local_timezone},
        "end": {"dateTime": "2026-08-01T16:00:00", "timeZone": settings.local_timezone},
    }


def test_update_calendar_event_all_day_fields_use_date_keys(monkeypatch):
    events = _FakeEvents(patch_result={"id": "e1"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.update_calendar_event("e1", start_iso="2026-08-01", end_iso="2026-08-02", all_day=True)

    assert events.patch_calls[0]["body"] == {
        "start": {"date": "2026-08-01"},
        "end": {"date": "2026-08-02"},
    }


def test_update_calendar_event_recurrence_only(monkeypatch):
    events = _FakeEvents(patch_result={"id": "e1"})
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    calendar_tools.update_calendar_event("e1", recurrence_rule="RRULE:FREQ=WEEKLY")

    assert events.patch_calls[0]["body"] == {"recurrence": ["RRULE:FREQ=WEEKLY"]}


def test_delete_calendar_event(monkeypatch):
    events = _FakeEvents(delete_result=None)
    monkeypatch.setattr(calendar_tools, "_calendar_client", lambda: _FakeService(events))

    result = calendar_tools.delete_calendar_event("e1")

    assert events.delete_calls == [{"calendarId": settings.primary_calendar_id, "eventId": "e1"}]
    assert result == {"deleted": True, "id": "e1"}

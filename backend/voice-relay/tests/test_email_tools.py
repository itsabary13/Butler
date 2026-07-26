"""Tests app/tools/email_tools.py's response-shaping and body-decoding
logic against a fake Gmail API client — never a real Google API call,
matching the rest of this suite's "no live provider calls" rule.
Establishes this repo's first Google-API-mocking pattern (calendar_tools.py
has no existing precedent to mirror)."""

import base64

from app.tools import email_tools


class _FakeExecutor:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeMessages:
    def __init__(self, list_result=None, get_results=None, modify_result=None):
        self.list_result = list_result
        self.get_results = get_results or {}
        self.modify_result = modify_result
        self.list_calls = []
        self.get_calls = []
        self.modify_calls = []

    def list(self, userId, q, maxResults):
        self.list_calls.append({"userId": userId, "q": q, "maxResults": maxResults})
        return _FakeExecutor(self.list_result)

    def get(self, userId, id, format=None, metadataHeaders=None):
        self.get_calls.append({"userId": userId, "id": id, "format": format, "metadataHeaders": metadataHeaders})
        return _FakeExecutor(self.get_results[id])

    def modify(self, userId, id, body):
        self.modify_calls.append({"userId": userId, "id": id, "body": body})
        return _FakeExecutor(self.modify_result)


class _FakeLabels:
    def __init__(self, list_result=None, create_result=None):
        self.list_result = list_result
        self.create_result = create_result
        self.create_calls = []

    def list(self, userId):
        return _FakeExecutor(self.list_result)

    def create(self, userId, body):
        self.create_calls.append(body)
        return _FakeExecutor(self.create_result)


class _FakeUsers:
    def __init__(self, messages, labels=None):
        self._messages = messages
        self._labels = labels

    def messages(self):
        return self._messages

    def labels(self):
        return self._labels


class _FakeService:
    def __init__(self, messages=None, labels=None):
        self._users = _FakeUsers(messages, labels)

    def users(self):
        return self._users


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _headers(**kwargs):
    return [{"name": name, "value": value} for name, value in kwargs.items()]


def test_list_recent_emails_shapes_response_and_passes_query_through(monkeypatch):
    messages = _FakeMessages(
        list_result={"messages": [{"id": "m1"}, {"id": "m2"}]},
        get_results={
            "m1": {
                "id": "m1",
                "snippet": "Hi there",
                "labelIds": ["UNREAD", "INBOX"],
                "payload": {"headers": _headers(From="a@example.com", Subject="Hello", Date="Mon, 1 Jan 2026")},
            },
            "m2": {
                "id": "m2",
                "snippet": "Already read",
                "labelIds": ["INBOX"],
                "payload": {"headers": _headers(From="b@example.com", Subject="Re: Hello", Date="Tue, 2 Jan 2026")},
            },
        },
    )
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.list_recent_emails(max_results=5, query="is:unread")

    assert messages.list_calls == [{"userId": "me", "q": "is:unread", "maxResults": 5}]
    assert result == [
        {"id": "m1", "from": "a@example.com", "subject": "Hello", "date": "Mon, 1 Jan 2026", "snippet": "Hi there", "unread": True},
        {"id": "m2", "from": "b@example.com", "subject": "Re: Hello", "date": "Tue, 2 Jan 2026", "snippet": "Already read", "unread": False},
    ]


def test_list_recent_emails_empty_inbox_returns_empty_list(monkeypatch):
    messages = _FakeMessages(list_result={})
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    assert email_tools.list_recent_emails() == []


def test_get_email_body_single_part_plain_text(monkeypatch):
    messages = _FakeMessages(get_results={
        "m1": {
            "id": "m1",
            "payload": {
                "headers": _headers(From="a@example.com", Subject="Hello", Date="Mon, 1 Jan 2026"),
                "mimeType": "text/plain",
                "body": {"data": _b64("Hello world")},
            },
        }
    })
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.get_email_body("m1")

    assert result == {"id": "m1", "from": "a@example.com", "subject": "Hello", "date": "Mon, 1 Jan 2026", "body": "Hello world"}


def test_get_email_body_multipart_prefers_plain_over_html(monkeypatch):
    messages = _FakeMessages(get_results={
        "m1": {
            "id": "m1",
            "payload": {
                "headers": _headers(From="a@example.com", Subject="Hi", Date="Mon, 1 Jan 2026"),
                "parts": [
                    {"mimeType": "text/html", "body": {"data": _b64("<p>Hi <b>there</b></p>")}},
                    {"mimeType": "text/plain", "body": {"data": _b64("Hi there")}},
                ],
            },
        }
    })
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.get_email_body("m1")

    assert result["body"] == "Hi there"


def test_get_email_body_falls_back_to_stripped_html_when_no_plain_part(monkeypatch):
    messages = _FakeMessages(get_results={
        "m1": {
            "id": "m1",
            "payload": {
                "headers": _headers(From="a@example.com", Subject="Hi", Date="Mon, 1 Jan 2026"),
                "parts": [
                    {"mimeType": "text/html", "body": {"data": _b64("<p>Hi <b>there</b>&nbsp;friend</p>")}},
                ],
            },
        }
    })
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.get_email_body("m1")

    assert result["body"] == "Hi there friend"


def test_get_email_body_handles_nested_multipart_alternative(monkeypatch):
    messages = _FakeMessages(get_results={
        "m1": {
            "id": "m1",
            "payload": {
                "headers": _headers(From="a@example.com", Subject="Hi", Date="Mon, 1 Jan 2026"),
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "parts": [
                            {"mimeType": "text/html", "body": {"data": _b64("<p>nested html</p>")}},
                            {"mimeType": "text/plain", "body": {"data": _b64("nested plain")}},
                        ],
                    }
                ],
            },
        }
    })
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.get_email_body("m1")

    assert result["body"] == "nested plain"


def test_mark_email_read_removes_unread_label(monkeypatch):
    messages = _FakeMessages(modify_result={"id": "m1", "labelIds": ["INBOX"]})
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages))

    result = email_tools.mark_email_read("m1")

    assert messages.modify_calls == [{"userId": "me", "id": "m1", "body": {"removeLabelIds": ["UNREAD"]}}]
    assert result == {"id": "m1", "unread": False}


def test_apply_email_label_reuses_existing_label(monkeypatch):
    labels = _FakeLabels(list_result={"labels": [{"id": "Label_1", "name": "Important"}]})
    messages = _FakeMessages(modify_result={"id": "m1", "labelIds": ["Label_1"]})
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages, labels=labels))

    result = email_tools.apply_email_label("m1", "Important")

    assert labels.create_calls == []
    assert messages.modify_calls == [{"userId": "me", "id": "m1", "body": {"addLabelIds": ["Label_1"]}}]
    assert result == {"id": "m1", "label": "Important"}


def test_apply_email_label_creates_label_when_missing(monkeypatch):
    labels = _FakeLabels(list_result={"labels": []}, create_result={"id": "Label_new", "name": "Important"})
    messages = _FakeMessages(modify_result={"id": "m1", "labelIds": ["Label_new"]})
    monkeypatch.setattr(email_tools, "_gmail_client", lambda: _FakeService(messages=messages, labels=labels))

    result = email_tools.apply_email_label("m1", "Important")

    assert labels.create_calls == [{"name": "Important"}]
    assert messages.modify_calls == [{"userId": "me", "id": "m1", "body": {"addLabelIds": ["Label_new"]}}]
    assert result == {"id": "m1", "label": "Important"}

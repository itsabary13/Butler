"""Direct Gmail API access — NOT via Claude Code's Gmail connector, since
this is a separate OS process with no access to that connector (same
reasoning as calendar_tools.py's own Calendar integration). Own OAuth
credentials, own token refresh; the refresh token is shared with
calendar_tools.py (one Google Cloud OAuth client, granted both
calendar.events and gmail.modify at once — see
scripts/google_oauth_setup.py).

Read (list/get) plus two narrow mutations (mark read, apply a label) —
no send/reply/delete, matching Calendar's own create-only precedent of
staying deliberately narrow rather than building every possible action
speculatively.
"""

import base64
import re
from html import unescape

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings


def _gmail_client():
    creds = Credentials(
        None,
        refresh_token=settings.google_oauth_refresh_token,
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    return build("gmail", "v1", credentials=creds)


def _header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_part_data(data: str) -> str:
    # Gmail body data is URL-safe base64 without padding.
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", text).strip()


def _extract_body(payload: dict) -> str:
    """Prefers text/plain; falls back to text/html (tags stripped) if
    that's all the message has. Walks nested multipart/alternative parts,
    since a message body isn't always at the top level."""
    if "parts" not in payload:
        data = payload.get("body", {}).get("data")
        if not data:
            return ""
        text = _decode_part_data(data)
        return _strip_html(text) if payload.get("mimeType") == "text/html" else text

    plain, html = None, None
    stack = list(payload["parts"])
    while stack:
        part = stack.pop()
        if "parts" in part:
            stack.extend(part["parts"])
            continue
        data = part.get("body", {}).get("data")
        if not data:
            continue
        if part.get("mimeType") == "text/plain" and plain is None:
            plain = _decode_part_data(data)
        elif part.get("mimeType") == "text/html" and html is None:
            html = _decode_part_data(data)

    if plain is not None:
        return plain
    if html is not None:
        return _strip_html(html)
    return ""


def list_recent_emails(max_results: int = 10, query: str = "") -> list[dict]:
    """query uses Gmail's own search syntax (e.g. "is:unread", "from:x") —
    passed straight through, it's a search filter the model constructs,
    not content written back anywhere."""
    service = _gmail_client()
    result = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    emails = []
    for item in result.get("messages", []):
        message = service.users().messages().get(
            userId="me", id=item["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        headers = message.get("payload", {}).get("headers", [])
        emails.append({
            "id": message.get("id"),
            "from": _header(headers, "From"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "snippet": message.get("snippet", ""),
            "unread": "UNREAD" in message.get("labelIds", []),
        })
    return emails


def get_email_body(message_id: str) -> dict:
    service = _gmail_client()
    message = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    return {
        "id": message.get("id"),
        "from": _header(headers, "From"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "body": _extract_body(payload),
    }


def mark_email_read(message_id: str) -> dict:
    service = _gmail_client()
    updated = service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    return {"id": updated.get("id"), "unread": "UNREAD" in updated.get("labelIds", [])}


def _find_or_create_label(service, label_name: str) -> str:
    existing = service.users().labels().list(userId="me").execute()
    for label in existing.get("labels", []):
        if label.get("name") == label_name:
            return label["id"]
    created = service.users().labels().create(
        userId="me", body={"name": label_name}
    ).execute()
    return created["id"]


def apply_email_label(message_id: str, label_name: str) -> dict:
    service = _gmail_client()
    label_id = _find_or_create_label(service, label_name)
    updated = service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()
    return {"id": updated.get("id"), "label": label_name}

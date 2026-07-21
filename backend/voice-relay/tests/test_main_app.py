from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lifespan_starts_and_stops_the_proactive_scheduler():
    # A plain TestClient(app) (used everywhere else in this file) never
    # triggers ASGI lifespan events at all — only entering it as a context
    # manager does, which is the only way to actually exercise app.main's
    # AsyncIOScheduler wiring (v1.6 addendum) rather than just importing it.
    # No assertion beyond "didn't raise": startup (scheduler.start(), the
    # job getting registered) and shutdown completing cleanly is the thing
    # being verified.
    with TestClient(app) as ctx_client:
        response = ctx_client.get("/health")
        assert response.status_code == 200


def test_webhook_rejects_wrong_path_secret():
    update = {"message": {"chat": {"id": 12345}, "voice": {"file_id": "abc"}}}
    response = client.post(
        "/telegram/webhook/wrong-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 401


def test_webhook_rejects_wrong_chat_id():
    update = {"message": {"chat": {"id": 99999}, "voice": {"file_id": "abc"}}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 401


def test_webhook_rejects_unhandled_message_type_with_wrong_secret():
    # The secret check must run BEFORE branching on message type — otherwise
    # an unauthenticated caller could distinguish "which message types this
    # endpoint handles" without ever presenting the right secret.
    update = {"message": {"chat": {"id": 12345}, "sticker": {"file_id": "xyz"}}}
    response = client.post(
        "/telegram/webhook/wrong-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-header-too"},
    )
    assert response.status_code == 401


def test_webhook_ignores_unhandled_message_type_once_authenticated():
    # A sticker (or any type with no voice/document/text extraction) is
    # silently accepted, not rejected — there's nothing to authorize since
    # nothing is going to be processed either way.
    update = {"message": {"chat": {"id": 12345}, "sticker": {"file_id": "xyz"}}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200


def test_webhook_drops_voice_message_under_one_second(monkeypatch):
    # Almost always an accidental tap — should never reach the pipeline.
    calls = []
    monkeypatch.setattr(main_module, "_process_voice_message", lambda chat_id, file_id: calls.append((chat_id, file_id)))

    update = {"message": {"chat": {"id": 12345}, "voice": {"file_id": "abc", "duration": 0}}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert calls == []


def test_webhook_schedules_processing_for_voice_message_at_least_one_second(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module, "_process_voice_message", lambda chat_id, file_id: calls.append((chat_id, file_id)))

    update = {"message": {"chat": {"id": 12345}, "voice": {"file_id": "abc", "duration": 3}}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert calls == [(12345, "abc")]


def test_webhook_schedules_processing_for_text_message(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module, "_process_text_message", lambda chat_id, text: calls.append((chat_id, text)))

    update = {"message": {"chat": {"id": 12345}, "text": "remember that my favorite color is blue"}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert calls == [(12345, "remember that my favorite color is blue")]


def test_webhook_rejects_text_message_from_non_owner_chat_id(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module, "_process_text_message", lambda chat_id, text: calls.append((chat_id, text)))

    update = {"message": {"chat": {"id": 99999}, "text": "hello"}}
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 401
    assert calls == []


def test_webhook_schedules_processing_for_document_message(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main_module,
        "_process_document_message",
        lambda chat_id, file_id, filename, caption: calls.append((chat_id, file_id, filename, caption)),
    )

    update = {
        "message": {
            "chat": {"id": 12345},
            "document": {"file_id": "doc-abc", "file_name": "passport_scan.pdf"},
            "caption": "my passport scan",
        }
    }
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert calls == [(12345, "doc-abc", "passport_scan.pdf", "my passport scan")]


def test_webhook_schedules_processing_for_photo_message(monkeypatch):
    # Photos (the compressed camera-roll/picker flow, distinct from a
    # "File" attachment) route through the same document pipeline with a
    # synthesized filename, since Telegram never gives a photo one.
    calls = []
    monkeypatch.setattr(
        main_module,
        "_process_document_message",
        lambda chat_id, file_id, filename, caption: calls.append((chat_id, file_id, filename, caption)),
    )

    update = {
        "message": {
            "chat": {"id": 12345},
            "photo": [
                {"file_id": "small", "width": 90, "height": 90},
                {"file_id": "large", "width": 1280, "height": 1280},
            ],
            "caption": "my new plant",
        }
    }
    response = client.post(
        "/telegram/webhook/test-webhook-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert response.status_code == 200
    assert calls == [(12345, "large", "photo.jpg", "my new plant")]

from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_webhook_rejects_non_voice_message_with_wrong_secret():
    # The secret check must run BEFORE branching on message type — otherwise
    # an unauthenticated caller could distinguish "voice vs. non-voice"
    # behavior without ever presenting the right secret.
    update = {"message": {"chat": {"id": 12345}, "text": "hello"}}
    response = client.post(
        "/telegram/webhook/wrong-secret",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-header-too"},
    )
    assert response.status_code == 401


def test_webhook_ignores_non_voice_message_once_authenticated():
    update = {"message": {"chat": {"id": 12345}, "text": "hello"}}
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

from fastapi.testclient import TestClient

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

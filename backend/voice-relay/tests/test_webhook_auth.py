from app import telegram
from app.config import settings


def test_authorized_when_secret_and_chat_id_match():
    assert telegram.is_authorized(
        settings.telegram_webhook_secret,
        settings.telegram_webhook_secret,
        settings.telegram_owner_chat_id,
    )


def test_rejected_when_path_secret_wrong():
    assert not telegram.is_authorized(
        "wrong-path-secret",
        settings.telegram_webhook_secret,
        settings.telegram_owner_chat_id,
    )


def test_rejected_when_header_secret_missing():
    assert not telegram.is_authorized(
        settings.telegram_webhook_secret,
        None,
        settings.telegram_owner_chat_id,
    )


def test_rejected_when_chat_id_not_owner():
    assert not telegram.is_authorized(
        settings.telegram_webhook_secret,
        settings.telegram_webhook_secret,
        "someone-elses-chat-id",
    )


def test_extract_voice_message_returns_none_for_text_message():
    update = {"message": {"chat": {"id": 1}, "text": "hello"}}
    assert telegram.extract_voice_message(update) is None


def test_extract_voice_message_returns_chat_id_file_id_and_duration():
    update = {"message": {"chat": {"id": 42}, "voice": {"file_id": "abc123", "duration": 5}}}
    result = telegram.extract_voice_message(update)
    assert result == {"chat_id": 42, "file_id": "abc123", "duration": 5}


def test_extract_voice_message_handles_missing_message_key():
    assert telegram.extract_voice_message({"edited_message": {}}) is None


def test_extract_document_message_returns_file_id_filename_and_caption():
    update = {
        "message": {
            "chat": {"id": 42},
            "document": {"file_id": "doc-abc", "file_name": "passport.pdf"},
            "caption": "my passport scan",
        }
    }
    result = telegram.extract_document_message(update)
    assert result == {"chat_id": 42, "file_id": "doc-abc", "filename": "passport.pdf", "caption": "my passport scan"}


def test_extract_document_message_defaults_caption_to_none_and_filename_when_missing():
    update = {"message": {"chat": {"id": 42}, "document": {"file_id": "doc-abc"}}}
    result = telegram.extract_document_message(update)
    assert result == {"chat_id": 42, "file_id": "doc-abc", "filename": "document", "caption": None}


def test_extract_document_message_returns_none_for_voice_message():
    update = {"message": {"chat": {"id": 1}, "voice": {"file_id": "abc"}}}
    assert telegram.extract_document_message(update) is None


def test_extract_text_message_returns_chat_id_and_text():
    update = {"message": {"chat": {"id": 42}, "text": "remember my wifi password is hunter2"}}
    result = telegram.extract_text_message(update)
    assert result == {"chat_id": 42, "text": "remember my wifi password is hunter2"}


def test_extract_text_message_returns_none_for_voice_message():
    update = {"message": {"chat": {"id": 1}, "voice": {"file_id": "abc"}}}
    assert telegram.extract_text_message(update) is None

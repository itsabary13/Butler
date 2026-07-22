"""Tests app/main.py's _handle_voice_message language gate (bug found live:
a Hebrew voice message got back a garbled, absurd-sounding voice reply,
because Piper has no Hebrew voice at all — see tts.UNSUPPORTED_LANGUAGES —
and was mispronouncing the Hebrew reply text with its English voice model
instead of failing cleanly. Fixed by sending text instead of attempting
synthesis whenever the detected input language is one Piper can't speak."""

import asyncio

import pytest

from app import main as main_module


@pytest.fixture(autouse=True)
def _stub_wiki_and_docs_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module.wiki_tools, "wiki_dir", lambda: tmp_path / "wiki")
    monkeypatch.setattr(main_module.document_tools, "docs_dir", lambda: tmp_path / "docs")
    monkeypatch.setattr(main_module.wiki_sync, "sync_before", lambda repo_dir: None)
    monkeypatch.setattr(main_module.wiki_sync, "sync_after", lambda repo_dir, commit_message: None)


def test_hebrew_reply_sends_text_not_voice(monkeypatch):
    monkeypatch.setattr(main_module.telegram, "download_file", _async_return(b"audio-bytes"))
    monkeypatch.setattr(main_module.stt, "transcribe", lambda audio_bytes: ("שלום", "he"))
    monkeypatch.setattr(main_module, "get_reply", lambda chat_id, text: "שלום, מה שלומך?")

    synthesize_calls = []
    monkeypatch.setattr(main_module.tts, "synthesize", lambda text: synthesize_calls.append(text))

    text_replies = []
    voice_replies = []
    monkeypatch.setattr(main_module.telegram, "send_text_reply", _async_capture(text_replies))
    monkeypatch.setattr(main_module.telegram, "send_voice_reply", _async_capture(voice_replies))

    asyncio.run(main_module._handle_voice_message("12345", "file-1"))

    assert synthesize_calls == []
    assert voice_replies == []
    assert text_replies == [("12345", "שלום, מה שלומך?")]


def test_english_reply_still_sends_voice(monkeypatch):
    monkeypatch.setattr(main_module.telegram, "download_file", _async_return(b"audio-bytes"))
    monkeypatch.setattr(main_module.stt, "transcribe", lambda audio_bytes: ("hello", "en"))
    monkeypatch.setattr(main_module, "get_reply", lambda chat_id, text: "Hi there.")
    monkeypatch.setattr(main_module.tts, "synthesize", lambda text: b"fake-audio-bytes")

    text_replies = []
    voice_replies = []
    monkeypatch.setattr(main_module.telegram, "send_text_reply", _async_capture(text_replies))
    monkeypatch.setattr(main_module.telegram, "send_voice_reply", _async_capture(voice_replies))

    asyncio.run(main_module._handle_voice_message("12345", "file-1"))

    assert text_replies == []
    assert voice_replies == [("12345", b"fake-audio-bytes")]


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


def _async_capture(calls):
    async def _fn(chat_id, payload):
        calls.append((chat_id, payload))

    return _fn

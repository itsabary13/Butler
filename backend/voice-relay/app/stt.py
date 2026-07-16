"""Speech-to-text via OpenAI. Telegram voice notes are complete OGG/Opus
clips (not a live stream), so a single batch transcription call is the
right fit — no streaming STT needed (docs/architecture/voice-relay.md).
"""

import io

from openai import OpenAI

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key)


def transcribe(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # the SDK uses this for the multipart filename/content-type hint
    result = _client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
    )
    return result.text.strip()

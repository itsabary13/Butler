"""Text-to-speech via OpenAI (docs/architecture/voice-relay.md's provider
choice — same account as STT, minimizes the number of external providers
for Phase 1). Output format 'opus' so it can go straight into a Telegram
voice note without a separate ffmpeg conversion step where possible;
telegram.py falls back to sendAudio if a given client needs a different
container.
"""

from openai import OpenAI

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key)


def synthesize(text: str, voice: str = "alloy") -> bytes:
    response = _client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="opus",
    )
    return response.read()

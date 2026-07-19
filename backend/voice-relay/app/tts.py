"""Text-to-speech via a local, offline Piper voice model (docs/architecture/
voice-relay.md's v1.1 addendum) — no account, no per-request billing.

Piper renders 16-bit PCM WAV directly; ffmpeg (already a Dockerfile/local
dependency for Telegram voice notes) converts that to Opus/OGG so replies
go straight into a native Telegram voice bubble. telegram.py falls back to
sendAudio if a given client needs a different container.
"""

import io
import subprocess
import wave

from piper import PiperVoice

from app.config import settings

_voice: PiperVoice | None = None


def _get_voice() -> PiperVoice:
    global _voice
    if _voice is None:
        config_path = settings.piper_voice_config_path or f"{settings.piper_voice_model_path}.json"
        _voice = PiperVoice.load(settings.piper_voice_model_path, config_path=config_path)
    return _voice


def _wav_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        _get_voice().synthesize_wav(text, wav_file)
    return buffer.getvalue()


def synthesize(text: str) -> bytes:
    wav_bytes = _wav_bytes(text)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-f", "ogg", "-c:a", "libopus", "pipe:1"],
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout

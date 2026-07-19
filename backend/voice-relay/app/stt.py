"""Speech-to-text via a local, offline faster-whisper model (docs/architecture/voice-relay.md's
v1.1 addendum) — no account, no per-request billing. Telegram voice notes are
complete OGG/Opus clips (not a live stream), so a single batch transcription
call is the right fit; no streaming STT needed.

The model is downloaded once (cached under the OS's default Hugging Face
cache dir, or WHISPER_MODEL_SIZE's download_root if set) on first use, then
loaded lazily so import time stays fast and tests never trigger a download.
"""

import io

from faster_whisper import WhisperModel

from app.config import settings

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes) -> str:
    audio_file = io.BytesIO(audio_bytes)
    segments, _info = _get_model().transcribe(audio_file)
    return " ".join(segment.text.strip() for segment in segments).strip()

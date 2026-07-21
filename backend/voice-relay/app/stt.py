"""Speech-to-text via a local, offline faster-whisper model (docs/architecture/voice-relay.md's
v1.1 addendum) — no account, no per-request billing. Telegram voice notes are
complete OGG/Opus clips (not a live stream), so a single batch transcription
call is the right fit; no streaming STT needed.

The model is downloaded once (cached under the OS's default Hugging Face
cache dir, or WHISPER_MODEL_SIZE's download_root if set) on first use, then
loaded lazily so import time stays fast and tests never trigger a download.

Language is restricted to ALLOWED_LANGUAGES (Whisper otherwise auto-detects
across ~99 languages, and a short or accented clip can land on an unrelated
one — seen in practice with a Hebrew message misdetected outright).
"""

import io

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from app.config import settings

_model: WhisperModel | None = None

ALLOWED_LANGUAGES = ("en", "he", "ru")


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    return _model


def _detect_allowed_language(model: WhisperModel, audio) -> str:
    """Whichever of ALLOWED_LANGUAGES scored highest, not Whisper's raw
    unrestricted top guess."""
    _language, _probability, all_language_probs = model.detect_language(audio=audio)
    allowed = [(lang, prob) for lang, prob in all_language_probs if lang in ALLOWED_LANGUAGES]
    return max(allowed, key=lambda pair: pair[1])[0]


def transcribe(audio_bytes: bytes) -> str:
    model = _get_model()
    audio = decode_audio(io.BytesIO(audio_bytes))
    language = _detect_allowed_language(model, audio)
    segments, _info = model.transcribe(audio, language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()

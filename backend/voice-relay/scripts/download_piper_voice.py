"""One-time, interactive Piper voice download. Run this manually once,
never as part of the running service.

Downloads a free, offline neural TTS voice model (~50-100MB, no account,
no billing) into backend/voice-relay/models/ (gitignored — a binary model
file, not source).

Usage:
    python scripts/download_piper_voice.py [voice-name]

Defaults to en_US-lessac-medium if no voice name is given. See
https://github.com/rhasspy/piper/blob/master/VOICES.md for the full list
of available voices/languages.

After it finishes, set in .env:
    PIPER_VOICE_MODEL_PATH=models/<voice-name>.onnx
"""

import sys
from pathlib import Path

from piper import download_voices

DEFAULT_VOICE = "en_US-lessac-medium"


def main() -> int:
    voice = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VOICE
    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Piper voice '{voice}' into {models_dir} ...")
    download_voices.download_voice(voice, models_dir)

    print("\nSuccess. Add this to backend/voice-relay/.env:\n")
    print(f"PIPER_VOICE_MODEL_PATH=models/{voice}.onnx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

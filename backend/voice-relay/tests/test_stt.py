"""Tests app/stt.py's language-restriction logic against a fake model —
never loads a real faster-whisper model (that's covered by the manual
round-trip smoke test, docs/tests/voice-relay.md's v1.1 addendum)."""

from app import stt


class _FakeModel:
    def __init__(self, all_language_probs):
        self._all_language_probs = all_language_probs

    def detect_language(self, audio):
        top_lang, top_prob = self._all_language_probs[0]
        return top_lang, top_prob, self._all_language_probs


def test_detect_allowed_language_ignores_disallowed_top_guess():
    # "de" scores highest overall, but isn't in ALLOWED_LANGUAGES — the
    # highest-scoring *allowed* language ("ru") should win instead.
    model = _FakeModel([("de", 0.9), ("ru", 0.05), ("en", 0.03), ("he", 0.01)])

    assert stt._detect_allowed_language(model, audio=None) == "ru"


def test_detect_allowed_language_picks_highest_among_allowed():
    model = _FakeModel([("he", 0.6), ("en", 0.3), ("ru", 0.1)])

    assert stt._detect_allowed_language(model, audio=None) == "he"

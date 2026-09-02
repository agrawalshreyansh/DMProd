import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.workers.transcription import TranscriptionError, transcribe_audio

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SPEECH_FIXTURE = FIXTURES_DIR / "speech_sample.wav"
# tiny, not the small model the worker actually runs — this is a plumbing
# check (does the binary + model invocation work), not a quality check.
TINY_MODEL_PATH = Path(__file__).parent.parent / "models" / "ggml-tiny.bin"

pytestmark = pytest.mark.skipif(
    not TINY_MODEL_PATH.exists(), reason="ggml-tiny.bin not present — see backend/.env.example"
)


def _make_silent_wav(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "2", str(path)],
        capture_output=True,
        check=True,
        timeout=15,
    )


def test_transcribe_audio_produces_text_from_real_speech(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model_path", str(TINY_MODEL_PATH))

    result = transcribe_audio(SPEECH_FIXTURE)

    assert result.text.strip() != ""
    assert result.language
    assert result.duration_seconds > 0


def test_transcribe_audio_returns_empty_text_for_silence(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "whisper_model_path", str(TINY_MODEL_PATH))
    silent_path = tmp_path / "silence.wav"
    _make_silent_wav(silent_path)

    result = transcribe_audio(silent_path)

    assert result.text == ""
    assert result.duration_seconds > 0


def test_transcribe_audio_raises_when_model_missing(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model_path", "/nonexistent/model.bin")

    with pytest.raises(TranscriptionError, match="model not found"):
        transcribe_audio(SPEECH_FIXTURE)


def test_transcribe_audio_raises_on_timeout(monkeypatch):
    monkeypatch.setattr(settings, "whisper_model_path", str(TINY_MODEL_PATH))
    import app.workers.transcription as transcription_module

    monkeypatch.setattr(transcription_module, "TRANSCRIBE_TIMEOUT_SECONDS", 0.001)

    with pytest.raises(TranscriptionError, match="timed out"):
        transcribe_audio(SPEECH_FIXTURE)

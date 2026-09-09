import httpx
import pytest

import app.workers.transcription as transcription_module
from app.config import settings
from app.workers.transcription import TranscriptionError, transcribe_audio

VERBOSE_JSON = {
    "text": " Hello world ",
    "language": "english",
    "duration": 3.5,
    "segments": [],
}


@pytest.fixture
def audio_file(tmp_path):
    path = tmp_path / "audio.wav"
    path.write_bytes(b"RIFF....WAVEfmt ")  # contents irrelevant — httpx.post is mocked
    return path


@pytest.fixture(autouse=True)
def _groq_key(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "test-key")


def _mock_post(monkeypatch, *, status_code=200, json_body=None, raises=None):
    def fake_post(*args, **kwargs):
        if raises is not None:
            raise raises
        return httpx.Response(status_code, json=json_body, request=httpx.Request("POST", transcription_module.GROQ_TRANSCRIPTION_URL))

    monkeypatch.setattr(transcription_module.httpx, "post", fake_post)


def test_transcribe_audio_parses_verbose_json(monkeypatch, audio_file):
    _mock_post(monkeypatch, json_body=VERBOSE_JSON)

    result = transcribe_audio(audio_file)

    assert result.text == "Hello world"
    assert result.language == "english"
    assert result.duration_seconds == 3.5


def test_transcribe_audio_returns_empty_text_for_silence(monkeypatch, audio_file):
    _mock_post(monkeypatch, json_body={"text": "", "language": "english", "duration": 2.0})

    result = transcribe_audio(audio_file)

    assert result.text == ""
    assert result.duration_seconds == 2.0


def test_transcribe_audio_raises_when_key_missing(monkeypatch, audio_file):
    monkeypatch.setattr(settings, "groq_api_key", "")

    with pytest.raises(TranscriptionError, match="GROQ_API_KEY is not set"):
        transcribe_audio(audio_file)


def test_transcribe_audio_raises_on_timeout(monkeypatch, audio_file):
    _mock_post(monkeypatch, raises=httpx.TimeoutException("slow"))

    with pytest.raises(TranscriptionError, match="timed out"):
        transcribe_audio(audio_file)


def test_transcribe_audio_raises_on_api_error(monkeypatch, audio_file):
    _mock_post(monkeypatch, status_code=400, json_body={"error": {"message": "bad audio"}})

    with pytest.raises(TranscriptionError, match="bad audio"):
        transcribe_audio(audio_file)

from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings

# OpenAI-compatible audio endpoint. Groq file limit is 25MB (free) / 100MB
# (dev tier); a 16kHz mono WAV reel is ~2KB/s * 100s so well under.
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
TRANSCRIBE_TIMEOUT_SECONDS = 300


class TranscriptionError(Exception):
    """Groq transcription is unconfigured, failed, or timed out."""


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration_seconds: float


def transcribe_audio(audio_path: Path) -> TranscriptionResult:
    """Transcribe `audio_path` (a 16kHz mono WAV from Phase 5) with Groq's
    hosted Whisper. `language` is auto-detected and returned by the API —
    not forced to a fixed language without evidence it's needed."""
    if not settings.groq_api_key:
        raise TranscriptionError("GROQ_API_KEY is not set")

    try:
        with audio_path.open("rb") as audio_file:
            response = httpx.post(
                GROQ_TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": (audio_path.name, audio_file, "audio/wav")},
                data={"model": settings.groq_whisper_model, "response_format": "verbose_json"},
                timeout=TRANSCRIBE_TIMEOUT_SECONDS,
            )
    except httpx.TimeoutException as exc:
        raise TranscriptionError(
            f"Groq transcription timed out after {TRANSCRIBE_TIMEOUT_SECONDS}s"
        ) from exc
    except httpx.HTTPError as exc:
        raise TranscriptionError(f"Groq transcription request failed: {exc}") from exc

    if response.status_code != 200:
        # Groq errors come back as {"error": {"message": ...}}.
        detail = response.text
        try:
            detail = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            pass
        raise TranscriptionError(f"Groq transcription failed ({response.status_code}): {detail}")

    data = response.json()
    return TranscriptionResult(
        text=data.get("text", "").strip(),
        language=data.get("language", ""),
        duration_seconds=float(data.get("duration") or 0.0),
    )

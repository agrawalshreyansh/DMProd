import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

TRANSCRIBE_TIMEOUT_SECONDS = 300

# whisper.cpp emits bracketed tags like [BLANK_AUDIO]/[MUSIC] for non-speech
# audio instead of an empty transcription array — strip them so a music-only
# reel ends up with an actually-empty `text`, not a literal "[BLANK_AUDIO]".
_BRACKETED_TAG = re.compile(r"\[[^\]]*\]")


class TranscriptionError(Exception):
    """whisper-cli failed, timed out, or the model file is missing."""


@dataclass
class TranscriptionResult:
    text: str
    language: str
    duration_seconds: float


def _probe_duration_seconds(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def transcribe_audio(audio_path: Path) -> TranscriptionResult:
    """Transcribe `audio_path` (a 16kHz mono WAV from Phase 5) via
    whisper.cpp. `language` is auto-detected — Hinglish audio may make that
    unreliable; not forced to a fixed language without evidence it's needed."""
    if not Path(settings.whisper_model_path).exists():
        raise TranscriptionError(f"whisper model not found at {settings.whisper_model_path}")

    with tempfile.TemporaryDirectory() as out_dir:
        out_base = Path(out_dir) / "out"
        cmd = [
            "whisper-cli",
            "-m",
            settings.whisper_model_path,
            "-f",
            str(audio_path),
            "-l",
            "auto",
            "-oj",
            "-of",
            str(out_base),
            "-np",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=TRANSCRIBE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise TranscriptionError(f"whisper-cli timed out after {TRANSCRIBE_TIMEOUT_SECONDS}s") from exc
        except FileNotFoundError as exc:
            raise TranscriptionError("whisper-cli is not installed") from exc

        if result.returncode != 0:
            stderr_lines = result.stderr.decode(errors="replace").strip().splitlines()
            raise TranscriptionError(stderr_lines[-1] if stderr_lines else "whisper-cli failed")

        json_path = out_base.with_suffix(".json")
        if not json_path.exists():
            raise TranscriptionError("whisper-cli reported success but no output was written")

        data = json.loads(json_path.read_text())

    segments = data.get("transcription", [])
    raw_text = " ".join(seg.get("text", "") for seg in segments)
    text = _BRACKETED_TAG.sub("", raw_text).strip()
    language = data.get("result", {}).get("language", "")

    return TranscriptionResult(
        text=text,
        language=language,
        duration_seconds=_probe_duration_seconds(audio_path),
    )

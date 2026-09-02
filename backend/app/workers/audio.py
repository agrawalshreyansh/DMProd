import subprocess
from pathlib import Path

EXTRACT_TIMEOUT_SECONDS = 60


class AudioExtractionError(Exception):
    """ffmpeg failed, timed out, or the input has no audio track — a
    missing-audio-track input isn't special-cased: ffmpeg itself errors
    when -vn leaves nothing to map to the output, so it lands here too."""


def extract_audio(video_path: Path) -> Path:
    """Extract a 16kHz mono WAV from `video_path` into the same directory —
    the format Phase 6's whisper.cpp step expects as input."""
    output_path = video_path.with_suffix(".wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=EXTRACT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise AudioExtractionError(f"ffmpeg timed out after {EXTRACT_TIMEOUT_SECONDS}s") from exc
    except FileNotFoundError as exc:
        raise AudioExtractionError("ffmpeg is not installed") from exc

    if result.returncode != 0:
        stderr_lines = result.stderr.decode(errors="replace").strip().splitlines()
        raise AudioExtractionError(stderr_lines[-1] if stderr_lines else "ffmpeg failed")

    if not output_path.exists():
        raise AudioExtractionError("ffmpeg reported success but no file was written")

    return output_path

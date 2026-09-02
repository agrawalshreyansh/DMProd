import subprocess
from pathlib import Path

import pytest

import app.workers.audio as audio_module
from app.workers.audio import AudioExtractionError, extract_audio

# Fixtures are synthesized with ffmpeg's lavfi test sources rather than
# checked into the repo — tiny, deterministic, no binary blobs in git.


def _make_video_with_audio(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=64x64:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


def _make_silent_video(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=64x64:rate=10",
            "-c:v",
            "libx264",
            "-an",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


def test_extract_audio_produces_a_16khz_mono_wav(tmp_path):
    video_path = tmp_path / "input.mp4"
    _make_video_with_audio(video_path)

    audio_path = extract_audio(video_path)

    assert audio_path == video_path.with_suffix(".wav")
    assert audio_path.exists()

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "csv=p=0",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    sample_rate, channels = probe.stdout.strip().split(",")
    assert sample_rate == "16000"
    assert channels == "1"


def test_extract_audio_raises_cleanly_on_corrupt_input(tmp_path):
    video_path = tmp_path / "corrupt.mp4"
    video_path.write_bytes(b"not a real video file")

    with pytest.raises(AudioExtractionError):
        extract_audio(video_path)


def test_extract_audio_raises_cleanly_when_no_audio_track(tmp_path):
    video_path = tmp_path / "silent.mp4"
    _make_silent_video(video_path)

    with pytest.raises(AudioExtractionError):
        extract_audio(video_path)


def test_extract_audio_raises_on_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_module, "EXTRACT_TIMEOUT_SECONDS", 0.001)
    video_path = tmp_path / "input.mp4"
    _make_video_with_audio(video_path)

    with pytest.raises(AudioExtractionError, match="timed out"):
        extract_audio(video_path)

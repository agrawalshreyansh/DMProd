import random
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app.models.reel import Reel, VisualEvent
from app.workers import visual_analysis as va_module
from app.workers.visual_analysis import (
    VisualAnalysisError,
    VisualAnalysisSchema,
    _VisualEventItem,
    analyze_frames,
    analyze_visuals,
    build_timeline,
    dedupe_frames,
    extract_frames,
)

def _noise_frame(path: Path, seed: int) -> None:
    """A textured (non-uniform) image, so phash actually varies between
    frames - a solid color collapses to the same hash regardless of color,
    which would make dedup trivially (and misleadingly) pass."""
    random.seed(seed)
    im = Image.new("RGB", (64, 64))
    px = im.load()
    for x in range(64):
        for y in range(64):
            px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    im.save(path)


def _fake_genai_client(parsed=None, text="{}", calls=None, raise_error=None):
    def _factory(api_key):
        def generate_content(*, model, contents, config):
            if calls is not None:
                calls.append({"api_key": api_key, "model": model, "contents": contents, "config": config})
            if raise_error is not None:
                raise raise_error
            return SimpleNamespace(parsed=parsed, text=text)

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    return _factory


def test_dedupe_frames_drops_near_duplicates_keeps_distinct(tmp_path):
    same_a = tmp_path / "frame_0001.jpg"
    same_b = tmp_path / "frame_0002.jpg"
    different = tmp_path / "frame_0003.jpg"
    _noise_frame(same_a, seed=1)
    _noise_frame(same_b, seed=1)  # identical seed -> identical image
    _noise_frame(different, seed=2)  # different seed -> visually distinct

    kept = dedupe_frames([same_a, same_b, different])

    assert kept == [same_a, different]


def test_extract_frames_samples_a_real_video(tmp_path):
    video_path = tmp_path / "clip.mp4"
    # 2s synthetic video, generated in-test rather than checking in a binary
    # fixture - same approach Phase 6 used for its `say`-generated audio clip.
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    out_dir = tmp_path / "frames"
    out_dir.mkdir()

    frames = extract_frames(video_path, out_dir)

    assert len(frames) >= 2  # ~1fps over a 2s clip
    assert all(f.exists() for f in frames)


def test_extract_frames_raises_on_missing_ffmpeg(tmp_path, monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(va_module.subprocess, "run", _raise)

    with pytest.raises(VisualAnalysisError, match="not installed"):
        extract_frames(tmp_path / "clip.mp4", tmp_path)


def test_extract_frames_raises_on_corrupt_video(tmp_path):
    bad_video = tmp_path / "not-a-video.mp4"
    bad_video.write_bytes(b"not actually a video")
    out_dir = tmp_path / "frames"
    out_dir.mkdir()

    with pytest.raises(VisualAnalysisError):
        extract_frames(bad_video, out_dir)


def test_analyze_frames_batches_all_keyframes_into_one_call(tmp_path, monkeypatch):
    frame_paths = [tmp_path / f"frame_{i:04d}.jpg" for i in (1, 2, 3)]
    for i, path in enumerate(frame_paths):
        _noise_frame(path, seed=i)

    calls = []
    parsed = VisualAnalysisSchema(
        events=[_VisualEventItem(timestamp_seconds=0.0, description="a slide with text", on_screen_text="Step 1")]
    )
    monkeypatch.setattr(va_module.genai, "Client", _fake_genai_client(parsed=parsed, calls=calls))

    events = analyze_frames(frame_paths, "sk-test")

    assert len(calls) == 1  # one batched call, not one per frame
    assert calls[0]["api_key"] == "sk-test"
    # 2 content items per frame (timestamp label + image)
    assert len(calls[0]["contents"]) == len(frame_paths) * 2
    assert events == [VisualEvent(timestamp_seconds=0.0, description="a slide with text", on_screen_text="Step 1")]


def test_analyze_frames_returns_empty_for_no_keyframes():
    assert analyze_frames([], "sk-test") == []


def test_analyze_frames_raises_when_response_unparseable(tmp_path, monkeypatch):
    path = tmp_path / "frame_0001.jpg"
    _noise_frame(path, seed=1)
    monkeypatch.setattr(va_module.genai, "Client", _fake_genai_client(parsed=None))

    with pytest.raises(VisualAnalysisError, match="no parseable"):
        analyze_frames([path], "sk-test")


def test_build_timeline_formats_timestamp_and_on_screen_text():
    events = [
        VisualEvent(timestamp_seconds=75.0, description="shows a book cover", on_screen_text="Atomic Habits"),
        VisualEvent(timestamp_seconds=5.0, description="talking to camera", on_screen_text=None),
    ]

    timeline = build_timeline(events)

    assert "[01:15] shows a book cover (on-screen: Atomic Habits)" in timeline
    assert "[00:05] talking to camera" in timeline
    assert "on-screen: None" not in timeline


def test_build_timeline_empty_for_no_events():
    assert build_timeline([]) == ""


@pytest.mark.asyncio
async def test_analyze_visuals_skips_when_no_key_configured(app, tmp_path, monkeypatch):
    monkeypatch.setattr(va_module.settings, "visual_analysis_gemini_api_key", "")
    reel = await Reel(reel_video_id="v1").insert()

    analyze_visuals(reel, tmp_path / "video.mp4", tmp_path)

    assert reel.visual_processing_status == "skipped"
    assert reel.visual_events == []


@pytest.mark.asyncio
async def test_analyze_visuals_populates_reel_on_success(app, tmp_path, monkeypatch):
    monkeypatch.setattr(va_module.settings, "visual_analysis_gemini_api_key", "sk-test")
    video_path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    parsed = VisualAnalysisSchema(
        events=[_VisualEventItem(timestamp_seconds=0.0, description="test pattern", on_screen_text=None)]
    )
    monkeypatch.setattr(va_module.genai, "Client", _fake_genai_client(parsed=parsed))
    reel = await Reel(reel_video_id="v1").insert()

    analyze_visuals(reel, video_path, tmp_path)

    assert reel.visual_processing_status == "done"
    assert len(reel.visual_events) == 1
    assert "test pattern" in reel.visual_summary


@pytest.mark.asyncio
async def test_analyze_visuals_never_raises_on_ffmpeg_failure(app, tmp_path, monkeypatch):
    # A failure here (bad video, Gemini error) must never propagate and
    # block the transcription-driven flow that already works without it.
    monkeypatch.setattr(va_module.settings, "visual_analysis_gemini_api_key", "sk-test")
    reel = await Reel(reel_video_id="v1").insert()
    bad_video = tmp_path / "not-a-video.mp4"
    bad_video.write_bytes(b"not actually a video")

    analyze_visuals(reel, bad_video, tmp_path)  # must not raise

    assert reel.visual_processing_status == "failed"


@pytest.mark.asyncio
async def test_analyze_visuals_never_raises_on_gemini_error(app, tmp_path, monkeypatch):
    monkeypatch.setattr(va_module.settings, "visual_analysis_gemini_api_key", "sk-test")
    video_path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=10",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    monkeypatch.setattr(
        va_module.genai, "Client", _fake_genai_client(raise_error=RuntimeError("gemini down"))
    )
    reel = await Reel(reel_video_id="v1").insert()

    analyze_visuals(reel, video_path, tmp_path)  # must not raise

    assert reel.visual_processing_status == "failed"

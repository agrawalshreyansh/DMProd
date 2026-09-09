import logging
import subprocess
from pathlib import Path

import imagehash
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

from app.config import settings
from app.models.reel import Reel, VisualEvent

logger = logging.getLogger("worker.visual_analysis")

EXTRACT_FPS = 1.0
EXTRACT_TIMEOUT_SECONDS = 60
# Hamming distance below which a frame is treated as "same as the last kept
# one" — a starting guess (common phash default), not yet tuned against
# real reels. ponytail: bump/lower once real footage is eyeballed.
DEDUPE_HASH_DISTANCE = 5
# Even after dedup, never send more than this many images in one Gemini
# call — bounds cost/latency regardless of how noisy a given reel's dedup
# turns out to be.
MAX_KEYFRAMES = 20
VISION_MODEL = "gemini-3.6-flash"

VISION_SYSTEM_INSTRUCTION = """\
You are given a sequence of frames sampled from a short-form video, each \
preceded by a line stating its timestamp in seconds. Describe what's \
visually happening at each frame - on-screen text, slides, product names, \
screen recordings, notable visual changes - in enough detail that someone \
who only reads your description (not watching the video) knows exactly \
what was shown. Copy any on-screen text verbatim into `on_screen_text` \
rather than paraphrasing it; leave it null when there is none. Skip frames \
that show nothing more than a person talking to camera with no meaningful \
on-screen content - only return events for frames actually worth noting."""

CAROUSEL_VISION_SYSTEM_INSTRUCTION = """\
You are given the images of an Instagram carousel post, in order, each \
preceded by a line stating its slide number. Describe what each slide \
shows - on-screen text, lists, product names, screenshots, diagrams, \
charts, notable visuals - in enough detail that someone who only reads \
your description (never seeing the post) knows exactly what was on each \
slide. Copy any on-screen text verbatim into `on_screen_text` rather than \
paraphrasing it; leave it null when there is none. For each event, set \
`timestamp_seconds` to that slide's number. Return one event per slide \
worth noting; skip slides that carry nothing beyond decoration."""


class VisualAnalysisError(Exception):
    """ffmpeg failed, or the Gemini vision call failed/returned nothing
    parseable. Always caught at the top level (`analyze_visuals`) - a
    failure here must never block the download/audio/transcribe flow that
    already works without this step."""


class _VisualEventItem(BaseModel):
    timestamp_seconds: float
    description: str
    on_screen_text: str | None = None


class VisualAnalysisSchema(BaseModel):
    events: list[_VisualEventItem]


def extract_frames(video_path: Path, out_dir: Path) -> list[Path]:
    """Sample `video_path` at EXTRACT_FPS into `out_dir`, one jpg per frame.
    Mirrors `app.workers.audio.extract_audio`'s ffmpeg-subprocess shape."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={EXTRACT_FPS}",
        str(out_dir / "frame_%04d.jpg"),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=EXTRACT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise VisualAnalysisError(f"ffmpeg timed out after {EXTRACT_TIMEOUT_SECONDS}s") from exc
    except FileNotFoundError as exc:
        raise VisualAnalysisError("ffmpeg is not installed") from exc

    if result.returncode != 0:
        stderr_lines = result.stderr.decode(errors="replace").strip().splitlines()
        raise VisualAnalysisError(stderr_lines[-1] if stderr_lines else "ffmpeg failed")

    return sorted(out_dir.glob("frame_*.jpg"))


def _frame_timestamp(frame_path: Path) -> float:
    index = int(frame_path.stem.split("_")[1])
    return (index - 1) / EXTRACT_FPS


def dedupe_frames(frame_paths: list[Path]) -> list[Path]:
    """Collapse consecutive near-identical frames to one representative
    each via perceptual hash - cheap, no vision model involved. A frame is
    kept only when it differs enough from the last *kept* frame (not its
    immediate predecessor), so a slow drift across many similar frames
    still gets caught relative to the last real keyframe, not reset every
    single frame."""
    kept: list[Path] = []
    last_hash = None
    for path in frame_paths:
        current_hash = imagehash.phash(Image.open(path))
        if last_hash is None or (current_hash - last_hash) >= DEDUPE_HASH_DISTANCE:
            kept.append(path)
            last_hash = current_hash
    return kept


def _cap_keyframes(frame_paths: list[Path]) -> list[Path]:
    """Even-sample down to MAX_KEYFRAMES if dedup still leaves too many.
    ponytail: even sampling, not clustering - revisit only if this loses
    real signal on actual reels."""
    if len(frame_paths) <= MAX_KEYFRAMES:
        return frame_paths
    step = len(frame_paths) / MAX_KEYFRAMES
    return [frame_paths[int(i * step)] for i in range(MAX_KEYFRAMES)]


def _run_vision(
    labeled_images: list[tuple[str, Path]], system_instruction: str, api_key: str
) -> list[VisualEvent]:
    """One batched Gemini vision call over every image - the actual cost
    lever is this being one call, not one per image. Each entry is a
    (label, path): the label line precedes its image in the prompt."""
    if not labeled_images:
        return []

    contents: list = []
    for label, path in labeled_images:
        contents.append(label)
        contents.append(Image.open(path))

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=VisualAnalysisSchema,
        ),
    )
    parsed: VisualAnalysisSchema | None = response.parsed
    if parsed is None:
        raise VisualAnalysisError("Gemini returned no parseable structured output")

    return [
        VisualEvent(
            timestamp_seconds=item.timestamp_seconds,
            description=item.description,
            on_screen_text=item.on_screen_text,
        )
        for item in parsed.events
    ]


def analyze_frames(frame_paths: list[Path], api_key: str) -> list[VisualEvent]:
    """Batched Gemini vision over reel keyframes, labelled by timestamp."""
    return _run_vision(
        [(f"Timestamp: {_frame_timestamp(p):.1f}s", p) for p in frame_paths],
        VISION_SYSTEM_INSTRUCTION,
        api_key,
    )


def build_timeline(events: list[VisualEvent]) -> str:
    """The merged text that actually reaches Phase 7's prompt - not the raw
    frames or raw Gemini response."""
    lines = []
    for event in events:
        minutes, seconds = divmod(int(event.timestamp_seconds), 60)
        line = f"[{minutes:02d}:{seconds:02d}] {event.description}"
        if event.on_screen_text:
            line += f" (on-screen: {event.on_screen_text})"
        lines.append(line)
    return "\n".join(lines)


def _carousel_slide_number(path: Path) -> int:
    """`slide_003.jpg` -> 3; 0 if the name has no digits (keeps sort stable)."""
    digits = "".join(c for c in path.stem if c.isdigit())
    return int(digits) if digits else 0


def build_slide_summary(events: list[VisualEvent]) -> str:
    """Carousel counterpart to `build_timeline` - slide numbers, not
    timestamps. This is the text that reaches Phase 7's prompt."""
    lines = []
    for event in events:
        line = f"Slide {int(event.timestamp_seconds)}: {event.description}"
        if event.on_screen_text:
            line += f" (on-screen: {event.on_screen_text})"
        lines.append(line)
    return "\n".join(lines)


def analyze_carousel(reel: Reel, image_paths: list[Path]) -> None:
    """Vision-only counterpart to `analyze_visuals` for carousel posts:
    every slide image goes to one Gemini call (no frame extraction, no
    dedup - the slides are already distinct), result written onto `reel`
    for the caller's `reel.save()` to persist.

    Same never-raises contract as `analyze_visuals`. Note the different
    weight: for a carousel there is no transcript, so this output plus the
    caption is the *entire* basis for task generation, not a supplement."""
    if not settings.visual_analysis_gemini_api_key:
        reel.visual_processing_status = "skipped"
        return

    reel.visual_processing_status = "processing"
    slides = _cap_keyframes(image_paths)  # IG carousels cap at 10 anyway
    labeled = [(f"Slide {_carousel_slide_number(p)}", p) for p in slides]
    try:
        events = _run_vision(
            labeled, CAROUSEL_VISION_SYSTEM_INSTRUCTION, settings.visual_analysis_gemini_api_key
        )
    except VisualAnalysisError as exc:
        logger.warning("carousel visual analysis failed reel_id=%s error=%s", reel.id, exc)
        reel.visual_processing_status = "failed"
        return
    except Exception as exc:  # Gemini SDK can raise its own error types too
        logger.warning("carousel visual analysis failed reel_id=%s error=%s", reel.id, exc)
        reel.visual_processing_status = "failed"
        return

    reel.visual_events = events
    reel.visual_summary = build_slide_summary(events)
    reel.visual_processing_status = "done"
    logger.info(
        "carousel visual analysis done reel_id=%s slides=%d events=%d",
        reel.id,
        len(slides),
        len(events),
    )


def analyze_visuals(reel: Reel, video_path: Path, tmp_dir: Path) -> None:
    """Extracts, dedupes, and analyzes keyframes from `video_path`, writing
    the result onto `reel` (not saved here - the caller's existing
    `reel.save()` right after this call persists it, same as every other
    pipeline step in `process_reel.py`).

    Never raises: this must never block the transcription-driven flow that
    already works without it - any failure just downgrades
    `visual_processing_status` to "failed" and moves on."""
    if not settings.visual_analysis_gemini_api_key:
        reel.visual_processing_status = "skipped"
        return

    reel.visual_processing_status = "processing"
    frames_dir = tmp_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    try:
        frames = extract_frames(video_path, frames_dir)
        keyframes = _cap_keyframes(dedupe_frames(frames))
        events = analyze_frames(keyframes, settings.visual_analysis_gemini_api_key)
    except VisualAnalysisError as exc:
        logger.warning("visual analysis failed reel_id=%s error=%s", reel.id, exc)
        reel.visual_processing_status = "failed"
        return
    except Exception as exc:  # Gemini SDK can raise its own error types too
        logger.warning("visual analysis failed reel_id=%s error=%s", reel.id, exc)
        reel.visual_processing_status = "failed"
        return

    reel.visual_events = events
    reel.visual_summary = build_timeline(events)
    reel.visual_processing_status = "done"
    logger.info(
        "visual analysis done reel_id=%s frames=%d keyframes=%d events=%d",
        reel.id,
        len(frames),
        len(keyframes),
        len(events),
    )

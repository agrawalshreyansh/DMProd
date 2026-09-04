import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from rq import Retry

from app.db import init_db
from app.models.reel import Reel
from app.models.user_reel import UserReel
from app.queue import get_queue
from app.workers.audio import AudioExtractionError, extract_audio
from app.workers.download import ReelDownloadError, download_reel
from app.workers.task_generation import generate_task
from app.workers.transcription import TranscriptionError, transcribe_audio
from app.workers.visual_analysis import analyze_visuals

logger = logging.getLogger("worker.process_reel")


async def process_reel_async(reel_id: str) -> None:
    """The pipeline for one reel. LLM task generation (Phase 7) slots in
    after transcription below, in this same invocation — that's why the
    temp dir isn't torn down until the end rather than inside each stage."""
    reel = await Reel.get(reel_id)
    if reel is None:
        logger.warning("process_reel: reel_id=%s not found", reel_id)
        return

    reel.status = "downloading"
    await reel.save()

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"reel-{reel.id}-"))
    try:
        await _run_pipeline(reel, tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _run_pipeline(reel: Reel, tmp_dir: Path) -> None:
    try:
        video_path = download_reel(reel, tmp_dir)
    except ReelDownloadError as exc:
        logger.warning("download failed reel_id=%s error=%s", reel.id, exc)
        reel.status = "failed"
        reel.error_message = str(exc)
        await reel.save()
        return

    reel.status = "downloaded"
    await reel.save()

    reel.status = "extracting_audio"
    await reel.save()
    try:
        audio_path = extract_audio(video_path)
    except AudioExtractionError as exc:
        logger.warning("audio extraction failed reel_id=%s error=%s", reel.id, exc)
        reel.status = "failed"
        reel.error_message = str(exc)
        await reel.save()
        return

    logger.info(
        "audio extracted reel_id=%s path=%s size_bytes=%d",
        reel.id,
        audio_path,
        audio_path.stat().st_size,
    )
    reel.status = "audio_extracted"
    await reel.save()

    reel.status = "transcribing"
    await reel.save()
    try:
        result = transcribe_audio(audio_path)
    except TranscriptionError as exc:
        logger.warning("transcription failed reel_id=%s error=%s", reel.id, exc)
        reel.status = "failed"
        reel.error_message = str(exc)
        await reel.save()
        return

    reel.transcript_text = result.text
    reel.transcript_language = result.language
    reel.transcript_duration_seconds = result.duration_seconds

    logger.info(
        "transcribed reel_id=%s language=%s chars=%d duration_seconds=%.1f",
        reel.id,
        result.language,
        len(result.text),
        result.duration_seconds,
    )

    # Phase 13: keyframe extraction + Gemini vision, on the same downloaded
    # video file while it's still on disk. Never raises - a visual-analysis
    # failure only downgrades `visual_processing_status`, it never blocks
    # this (already working) transcript-driven flow.
    analyze_visuals(reel, video_path, tmp_dir)

    reel.status = "transcribed"
    await reel.save()

    # Task generation is per-(user, reel) — each user has their own Gemini
    # key, so it can't be deduped on the shared Reel the way download/audio/
    # transcribe are. Covers every user who shared this reel while it was
    # still processing, not just whoever's share triggered this run.
    user_reels = await UserReel.find(UserReel.reel_id == str(reel.id)).to_list()
    for user_reel in user_reels:
        get_queue().enqueue(generate_task, str(user_reel.id), retry=Retry(max=3))


def process_reel(reel_id: str) -> None:
    """RQ job entrypoint. RQ calls this as a plain sync function, so each
    invocation gets its own event loop and Motor client rather than reusing
    one across `asyncio.run()` calls, which Motor doesn't support.

    ponytail: reconnects to Mongo on every job — fine at this phase's volume;
    switch to a long-lived worker loop (own event loop, one client) if
    per-job connect overhead ever matters.
    """

    async def _run() -> None:
        await init_db()
        await process_reel_async(reel_id)

    asyncio.run(_run())

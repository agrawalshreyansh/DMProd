import pytest

from app.models.reel import Reel
from app.models.user_reel import UserReel
from app.queue import get_queue
from app.workers import process_reel as process_reel_module
from app.workers.audio import AudioExtractionError
from app.workers.download import ReelDownloadError
from app.workers.process_reel import process_reel_async
from app.workers.transcription import TranscriptionError, TranscriptionResult

pytestmark = pytest.mark.asyncio


def _fake_download_reel(captured):
    def _download(reel, dest_dir):
        captured["dir"] = dest_dir
        video_path = dest_dir / "video.mp4"
        video_path.write_bytes(b"fake video bytes")
        return video_path

    return _download


def _fake_extract_audio(video_path):
    audio_path = video_path.with_suffix(".wav")
    audio_path.write_bytes(b"fake wav bytes")
    return audio_path


def _fake_transcribe_audio(audio_path):
    return TranscriptionResult(text="hello world", language="en", duration_seconds=3.5)


async def test_process_reel_missing_reel_id_does_not_raise(app):
    await process_reel_async("000000000000000000000000")


async def test_process_reel_succeeds_through_to_transcribed(app, monkeypatch):
    captured = {}
    monkeypatch.setattr(process_reel_module, "download_reel", _fake_download_reel(captured))
    monkeypatch.setattr(process_reel_module, "extract_audio", _fake_extract_audio)
    monkeypatch.setattr(process_reel_module, "transcribe_audio", _fake_transcribe_audio)

    reel = await Reel(status="queued").insert()
    await process_reel_async(str(reel.id))

    updated = await Reel.get(reel.id)
    assert updated.status == "transcribed"
    assert updated.error_message is None
    assert not captured["dir"].exists()
    assert updated.transcript_text == "hello world"
    assert updated.transcript_language == "en"
    assert updated.transcript_duration_seconds == 3.5


async def test_process_reel_retry_overwrites_transcript_fields_idempotently(app, monkeypatch):
    captured = {}
    monkeypatch.setattr(process_reel_module, "download_reel", _fake_download_reel(captured))
    monkeypatch.setattr(process_reel_module, "extract_audio", _fake_extract_audio)
    monkeypatch.setattr(process_reel_module, "transcribe_audio", _fake_transcribe_audio)

    reel = await Reel(status="queued").insert()
    await process_reel_async(str(reel.id))
    await process_reel_async(str(reel.id))

    updated = await Reel.get(reel.id)
    assert updated.status == "transcribed"
    assert updated.transcript_text == "hello world"


async def test_process_reel_enqueues_task_generation_for_every_associated_user_reel(
    app, monkeypatch
):
    monkeypatch.setattr(process_reel_module, "download_reel", _fake_download_reel({}))
    monkeypatch.setattr(process_reel_module, "extract_audio", _fake_extract_audio)
    monkeypatch.setattr(process_reel_module, "transcribe_audio", _fake_transcribe_audio)

    reel = await Reel(status="queued").insert()
    share_one = await UserReel(
        user_id="user-a", reel_id=str(reel.id), sender_ig_id="1", message_id="m1"
    ).insert()
    share_two = await UserReel(
        user_id="user-b", reel_id=str(reel.id), sender_ig_id="2", message_id="m2"
    ).insert()

    await process_reel_async(str(reel.id))

    jobs = get_queue().jobs
    assert len(jobs) == 2
    assert all(j.func_name == "app.workers.task_generation.generate_task" for j in jobs)
    assert {j.args[0] for j in jobs} == {str(share_one.id), str(share_two.id)}


async def test_process_reel_marks_failed_on_download_error(app, monkeypatch):
    captured = {}

    def failing_download_reel(reel, dest_dir):
        captured["dir"] = dest_dir
        raise ReelDownloadError("resolution failed")

    monkeypatch.setattr(process_reel_module, "download_reel", failing_download_reel)

    reel = await Reel(status="queued").insert()
    await process_reel_async(str(reel.id))

    updated = await Reel.get(reel.id)
    assert updated.status == "failed"
    assert updated.error_message == "resolution failed"
    assert not captured["dir"].exists()


async def test_process_reel_marks_failed_on_audio_extraction_error(app, monkeypatch):
    captured = {}
    monkeypatch.setattr(process_reel_module, "download_reel", _fake_download_reel(captured))

    def failing_extract_audio(video_path):
        raise AudioExtractionError("ffmpeg boom")

    monkeypatch.setattr(process_reel_module, "extract_audio", failing_extract_audio)

    reel = await Reel(status="queued").insert()
    await process_reel_async(str(reel.id))

    updated = await Reel.get(reel.id)
    assert updated.status == "failed"
    assert updated.error_message == "ffmpeg boom"
    assert not captured["dir"].exists()


async def test_process_reel_marks_failed_on_transcription_error(app, monkeypatch):
    captured = {}
    monkeypatch.setattr(process_reel_module, "download_reel", _fake_download_reel(captured))
    monkeypatch.setattr(process_reel_module, "extract_audio", _fake_extract_audio)

    def failing_transcribe_audio(audio_path):
        raise TranscriptionError("whisper boom")

    monkeypatch.setattr(process_reel_module, "transcribe_audio", failing_transcribe_audio)

    reel = await Reel(status="queued").insert()
    await process_reel_async(str(reel.id))

    updated = await Reel.get(reel.id)
    assert updated.status == "failed"
    assert updated.error_message == "whisper boom"
    assert not captured["dir"].exists()
    assert updated.transcript_text is None

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.reel import Reel
from app.models.user_reel import UserReel
from app.queue import get_queue
from app.services.credentials import CredentialService
from app.workers import task_generation as task_generation_module
from app.workers.task_generation import TaskGenerationSchema, generate_task_async

pytestmark = pytest.mark.asyncio


def _fake_genai_client(parsed=None, text="{}", calls=None, raise_error=None):
    def _factory(api_key):
        def generate_content(*, model, contents, config):
            if calls is not None:
                calls.append(
                    {"api_key": api_key, "model": model, "contents": contents, "config": config}
                )
            if raise_error is not None:
                raise raise_error
            return SimpleNamespace(parsed=parsed, text=text)

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    return _factory


async def _make_reel_and_share(user_id="user-1", transcript="hello", caption="a caption"):
    reel = await Reel(
        status="transcribed", transcript_text=transcript, caption=caption
    ).insert()
    user_reel = await UserReel(
        user_id=user_id, reel_id=str(reel.id), sender_ig_id="ig1", message_id="m1"
    ).insert()
    return reel, user_reel


async def test_build_prompt_includes_caption_and_transcript():
    prompt = task_generation_module._build_prompt("transcript text", "caption text")
    assert "transcript text" in prompt
    assert "caption text" in prompt


async def test_build_prompt_marks_missing_caption_or_transcript_explicitly():
    # The model should be told a field is genuinely absent, not silently
    # handed a prompt with that section missing — an empty caption isn't
    # the same signal as no caption at all.
    prompt = task_generation_module._build_prompt("", "caption only")
    assert "unavailable" in prompt
    assert "caption only" in prompt

    prompt = task_generation_module._build_prompt("transcript only", "")
    assert "none provided" in prompt
    assert "transcript only" in prompt


async def test_build_prompt_includes_visual_summary_or_explicit_marker():
    # Phase 13: a third input, always present - either the real timeline or
    # an explicit "(none)" marker, never a silent omission.
    prompt = task_generation_module._build_prompt("t", "c", "[00:05] shows a book cover")
    assert "[00:05] shows a book cover" in prompt

    prompt = task_generation_module._build_prompt("t", "c")
    assert "(none)" in prompt


async def test_system_instruction_forbids_comment_instruction_when_unlock_keyword_set():
    # The app already follows/comments automatically (Phase 9) - the
    # user-facing task must never tell them to do it themselves.
    instruction = task_generation_module.SYSTEM_INSTRUCTION
    assert "must NEVER instruct the user to comment" in instruction


async def test_system_instruction_requires_surfacing_visual_specifics():
    instruction = task_generation_module.SYSTEM_INSTRUCTION
    assert "key_points entry" in instruction


async def test_system_instruction_covers_classification_and_actionability():
    instruction = task_generation_module.SYSTEM_INSTRUCTION
    for task_type in ["action_item", "event_reminder", "resource_reference", "content_idea", "other"]:
        assert task_type in instruction
    assert "not" in instruction and "summary" in instruction  # explicitly rules out vague recaps
    assert "next step" in instruction or "what to do" in instruction


async def test_generate_task_creates_task_from_valid_response(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    reel, user_reel = await _make_reel_and_share()

    calls = []
    parsed = TaskGenerationSchema(
        task_type="action_item",
        title="Try the recipe",
        details=TaskDetails(description="Make the pasta dish shown"),
        due_date=None,
    )
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed, calls=calls)
    )

    await generate_task_async(str(user_reel.id))

    task = await GeneratedTask.find_one(GeneratedTask.user_id == "user-1")
    assert task is not None
    assert task.reel_id == str(reel.id)
    assert task.task_type == "action_item"
    assert task.title == "Try the recipe"
    assert task.details.description == "Make the pasta dish shown"
    assert task.status == "not_started"

    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "generated"
    assert len(calls) == 1
    assert calls[0]["api_key"] == "sk-test"
    assert calls[0]["config"].system_instruction == task_generation_module.SYSTEM_INSTRUCTION

    jobs = get_queue().jobs
    assert len(jobs) == 1
    assert jobs[0].func_name == "app.workers.push.push_task"
    assert jobs[0].args[0] == str(task.id)


async def test_generate_task_includes_visual_summary_in_prompt(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    reel, user_reel = await _make_reel_and_share()
    reel.visual_summary = "[00:03] slide reads Atomic Habits"
    await reel.save()

    calls = []
    parsed = TaskGenerationSchema(
        task_type="resource_reference", title="Read the book", details=TaskDetails()
    )
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed, calls=calls)
    )

    await generate_task_async(str(user_reel.id))

    assert "Atomic Habits" in calls[0]["contents"]


async def test_generate_task_stores_reminder_lead_days_when_due_date_present(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    parsed = TaskGenerationSchema(
        task_type="event_reminder",
        title="Apply for the internship",
        details=TaskDetails(),
        due_date="2026-09-23",
        reminder_lead_days=3,
    )
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed))

    await generate_task_async(str(user_reel.id))

    task = await GeneratedTask.find_one(GeneratedTask.user_id == "user-1")
    assert task.reminder_lead_days == 3


async def test_generate_task_forces_reminder_lead_days_zero_without_due_date(app, monkeypatch):
    # Defensive: a due_date-less reminder has nothing to count backward
    # from, regardless of what Gemini returned.
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    parsed = TaskGenerationSchema(
        task_type="action_item",
        title="Try the recipe",
        details=TaskDetails(),
        due_date=None,
        reminder_lead_days=5,
    )
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed))

    await generate_task_async(str(user_reel.id))

    task = await GeneratedTask.find_one(GeneratedTask.user_id == "user-1")
    assert task.reminder_lead_days == 0


async def test_generate_task_clamps_out_of_range_reminder_lead_days(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    parsed = TaskGenerationSchema(
        task_type="event_reminder",
        title="Apply for the internship",
        details=TaskDetails(),
        due_date="2026-09-23",
        reminder_lead_days=50,
    )
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed))

    await generate_task_async(str(user_reel.id))

    task = await GeneratedTask.find_one(GeneratedTask.user_id == "user-1")
    assert task.reminder_lead_days == 7


async def test_generate_task_marks_failed_when_response_unparseable(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()

    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=None))

    await generate_task_async(str(user_reel.id))

    assert await GeneratedTask.find_one(GeneratedTask.user_id == "user-1") is None
    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert "no parseable" in updated_share.task_generation_error
    assert get_queue().jobs == []


async def test_generate_task_marks_failed_on_gemini_error(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()

    monkeypatch.setattr(
        task_generation_module.genai,
        "Client",
        _fake_genai_client(raise_error=RuntimeError("rate limited")),
    )

    await generate_task_async(str(user_reel.id))

    assert await GeneratedTask.find_one(GeneratedTask.user_id == "user-1") is None
    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert updated_share.task_generation_error == "rate limited"


async def test_generate_task_reraises_on_server_error_so_rq_retries(app, monkeypatch):
    # A 503 from Gemini being overloaded is transient — the job must raise
    # so RQ's Retry(max=3) (set where generate_task is enqueued) actually
    # retries it, instead of getting swallowed and marked permanently failed
    # on the first hiccup.
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    error = genai_errors.ServerError(503, {"message": "high demand", "status": "UNAVAILABLE"})
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(raise_error=error)
    )

    with pytest.raises(genai_errors.ServerError):
        await generate_task_async(str(user_reel.id))

    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "pending"  # untouched, not marked failed


async def test_generate_task_reraises_on_rate_limit_so_rq_retries(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    error = genai_errors.ClientError(429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"})
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(raise_error=error)
    )

    with pytest.raises(genai_errors.ClientError):
        await generate_task_async(str(user_reel.id))

    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "pending"


async def test_generate_task_marks_failed_on_non_retryable_client_error(app, monkeypatch):
    # A 400 (bad request, e.g. malformed prompt) won't succeed on retry —
    # keep the existing swallow-and-mark-failed behavior for these.
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()
    error = genai_errors.ClientError(400, {"message": "bad request", "status": "INVALID_ARGUMENT"})
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(raise_error=error)
    )

    await generate_task_async(str(user_reel.id))

    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert "bad request" in updated_share.task_generation_error


async def test_generate_task_fails_cleanly_without_gemini_key(app, monkeypatch):
    _, user_reel = await _make_reel_and_share()

    calls = []
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(calls=calls))

    await generate_task_async(str(user_reel.id))

    assert calls == []
    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert updated_share.task_generation_error == "no Gemini key configured"


async def test_build_prompt_for_carousel_labels_slides_and_marks_no_audio():
    prompt = task_generation_module._build_prompt(
        "", "book list caption", "Slide 1: a stack of books", media_type="carousel"
    )
    assert "carousel post" in prompt
    assert "no audio track" in prompt
    assert "Slide-by-slide visual description" in prompt
    assert "Slide 1: a stack of books" in prompt
    assert "book list caption" in prompt


async def test_carousel_visual_summary_alone_is_sufficient_content(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    reel = await Reel(
        status="transcribed",
        media_type="carousel",
        transcript_text=None,
        caption=None,
        visual_summary="Slide 1: a list of 5 books with titles",
    ).insert()
    user_reel = await UserReel(
        user_id="user-1", reel_id=str(reel.id), sender_ig_id="ig1", message_id="m1"
    ).insert()

    calls = []
    parsed = TaskGenerationSchema(
        task_type="resource_reference",
        title="Read the 5 books from the carousel",
        details=TaskDetails(description="Save these 5 books"),
        due_date=None,
    )
    monkeypatch.setattr(
        task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed, calls=calls)
    )

    await generate_task_async(str(user_reel.id))

    assert len(calls) == 1
    task = await GeneratedTask.find_one(GeneratedTask.user_id == "user-1")
    assert task is not None and task.task_type == "resource_reference"
    assert (await UserReel.get(user_reel.id)).task_generation_status == "generated"


async def test_generate_task_skips_gemini_call_when_content_is_empty(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share(transcript="", caption="")

    calls = []
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(calls=calls))

    await generate_task_async(str(user_reel.id))

    assert calls == []
    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert updated_share.task_generation_error == "insufficient_content"


async def test_generate_task_is_idempotent_when_already_generated(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    reel, user_reel = await _make_reel_and_share()
    await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="other",
        title="Existing",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    calls = []
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(calls=calls))

    await generate_task_async(str(user_reel.id))

    assert calls == []
    tasks = await GeneratedTask.find(GeneratedTask.user_id == "user-1").to_list()
    assert len(tasks) == 1


async def test_generate_task_missing_user_reel_does_not_raise(app):
    await generate_task_async("000000000000000000000000")


async def test_generate_task_triggers_comment_unlock_when_keyword_present(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    reel, user_reel = await _make_reel_and_share()
    reel.url = "https://www.instagram.com/reel/abc/"
    reel.creator_username = "creator1"
    await reel.save()

    parsed = TaskGenerationSchema(
        task_type="resource_reference",
        title="Get the guide",
        details=TaskDetails(),
        comment_to_unlock_keyword="YES",
    )
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed))

    calls = []

    async def _fake_trigger(reel_arg, keyword):
        calls.append((str(reel_arg.id), keyword))

    monkeypatch.setattr(task_generation_module, "trigger_comment_unlock", _fake_trigger)

    await generate_task_async(str(user_reel.id))

    assert calls == [(str(reel.id), "YES")]


async def test_generate_task_does_not_trigger_comment_unlock_without_keyword(app, monkeypatch):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-test"})
    _, user_reel = await _make_reel_and_share()

    parsed = TaskGenerationSchema(
        task_type="action_item", title="Do the thing", details=TaskDetails()
    )
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(parsed=parsed))

    calls = []

    async def _fake_trigger(reel_arg, keyword):
        calls.append((str(reel_arg.id), keyword))

    monkeypatch.setattr(task_generation_module, "trigger_comment_unlock", _fake_trigger)

    await generate_task_async(str(user_reel.id))

    assert calls == []

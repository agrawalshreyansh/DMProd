from types import SimpleNamespace

import pytest

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


async def test_generate_task_fails_cleanly_without_gemini_key(app, monkeypatch):
    _, user_reel = await _make_reel_and_share()

    calls = []
    monkeypatch.setattr(task_generation_module.genai, "Client", _fake_genai_client(calls=calls))

    await generate_task_async(str(user_reel.id))

    assert calls == []
    updated_share = await UserReel.get(user_reel.id)
    assert updated_share.task_generation_status == "failed"
    assert updated_share.task_generation_error == "no Gemini key configured"


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

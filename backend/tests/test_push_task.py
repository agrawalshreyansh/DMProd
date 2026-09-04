import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.integration import Integration
from app.models.preference import Preference
from app.models.push_log import PushLog
from app.workers import push as push_module
from app.workers.push import push_task_async

pytestmark = pytest.mark.asyncio


def _fake_push_to_notion(url=None, page_id="page-1", raise_error=None, calls=None):
    async def _push(task, integration, existing_page_id=None):
        if calls is not None:
            calls.append({"task_id": task.id, "existing_page_id": existing_page_id})
        if raise_error is not None:
            raise raise_error
        return url, page_id

    return _push


async def _make_task(user_id="user-1", task_type="action_item", **overrides):
    fields = dict(
        user_id=user_id,
        task_type=task_type,
        title="a task",
        details=TaskDetails(),
        raw_llm_response="{}",
    )
    fields.update(overrides)
    return await GeneratedTask(**fields).insert()


async def test_push_task_routes_to_notion_and_logs_success(app, monkeypatch):
    task = await _make_task()
    await Preference(user_id="user-1", task_type_routing={"action_item": "notion"}).insert()
    await Integration(user_id="user-1", type="notion", target_config={}).insert()
    monkeypatch.setattr(
        push_module, "push_to_notion", _fake_push_to_notion(url="https://notion.so/abc")
    )

    await push_task_async(str(task.id))

    log = await PushLog.find_one(PushLog.generated_task_id == str(task.id))
    assert log is not None
    assert log.status == "success"
    assert log.external_ref_url == "https://notion.so/abc"
    assert log.integration_type == "notion"


async def test_push_task_null_routing_does_nothing(app, monkeypatch):
    task = await _make_task(task_type="content_idea")
    await Preference(user_id="user-1", task_type_routing={"content_idea": None}).insert()
    monkeypatch.setattr(push_module, "push_to_notion", _fake_push_to_notion())

    await push_task_async(str(task.id))

    assert await PushLog.find(PushLog.generated_task_id == str(task.id)).count() == 0


async def test_push_task_missing_preference_does_nothing(app):
    task = await _make_task()
    await push_task_async(str(task.id))
    assert await PushLog.find(PushLog.generated_task_id == str(task.id)).count() == 0


async def test_push_task_logs_failure_when_integration_not_connected(app):
    task = await _make_task()
    await Preference(user_id="user-1", task_type_routing={"action_item": "notion"}).insert()

    await push_task_async(str(task.id))

    log = await PushLog.find_one(PushLog.generated_task_id == str(task.id))
    assert log is not None
    assert log.status == "failed"
    assert "not connected" in log.error_message


async def test_push_task_failure_is_logged_and_isolated_from_other_tasks(app, monkeypatch):
    failing_task = await _make_task(task_type="action_item", reel_id="reel-1")
    succeeding_task = await _make_task(task_type="content_idea", reel_id="reel-2")
    await Preference(
        user_id="user-1",
        task_type_routing={"action_item": "notion", "content_idea": "notion"},
    ).insert()
    await Integration(user_id="user-1", type="notion", target_config={}).insert()

    async def _push(task, integration, existing_page_id=None):
        if task.task_type == "action_item":
            raise RuntimeError("Notion API down")
        return "https://notion.so/ok", "page-ok"

    monkeypatch.setattr(push_module, "push_to_notion", _push)

    await push_task_async(str(failing_task.id))
    await push_task_async(str(succeeding_task.id))

    failed_log = await PushLog.find_one(PushLog.generated_task_id == str(failing_task.id))
    assert failed_log.status == "failed"
    assert failed_log.error_message == "Notion API down"

    ok_log = await PushLog.find_one(PushLog.generated_task_id == str(succeeding_task.id))
    assert ok_log.status == "success"
    assert ok_log.external_ref_url == "https://notion.so/ok"


async def test_push_task_missing_generated_task_does_not_raise(app):
    await push_task_async("000000000000000000000000")


async def test_push_task_routes_to_google_calendar_and_logs_success(app, monkeypatch):
    task = await _make_task(task_type="event_reminder")
    await Preference(
        user_id="user-1", task_type_routing={"event_reminder": "google_calendar"}
    ).insert()
    await Integration(user_id="user-1", type="google_calendar", target_config={}).insert()

    async def _push(task, integration, existing_event_id=None):
        return "https://calendar.google.com/event?eid=abc", "event-abc"

    monkeypatch.setattr(push_module, "push_to_gcal", _push)

    await push_task_async(str(task.id))

    log = await PushLog.find_one(PushLog.generated_task_id == str(task.id))
    assert log is not None
    assert log.status == "success"
    assert log.integration_type == "google_calendar"
    assert log.external_ref_url == "https://calendar.google.com/event?eid=abc"
    assert log.external_ref_id == "event-abc"


async def test_push_task_updates_existing_record_on_repush_not_a_new_one(app, monkeypatch):
    # The actual bug report: a re-push (e.g. Phase 9 enriching a task after
    # a comment-unlock DM reply) must update the record it already made
    # instead of creating a duplicate with the same title.
    task = await _make_task()
    await Preference(user_id="user-1", task_type_routing={"action_item": "notion"}).insert()
    await Integration(user_id="user-1", type="notion", target_config={}).insert()
    calls = []
    monkeypatch.setattr(
        push_module,
        "push_to_notion",
        _fake_push_to_notion(url="https://notion.so/abc", page_id="page-1", calls=calls),
    )

    await push_task_async(str(task.id))  # first push — nothing to update yet
    await push_task_async(str(task.id))  # re-push — should update page-1

    assert calls[0]["existing_page_id"] is None
    assert calls[1]["existing_page_id"] == "page-1"
    logs = await PushLog.find(PushLog.generated_task_id == str(task.id)).to_list()
    assert len(logs) == 2  # one audit row per push attempt
    assert all(log.status == "success" for log in logs)

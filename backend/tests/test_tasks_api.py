from datetime import datetime, timedelta, timezone

import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.reel import Reel

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"], resp.json()["user_id"]


async def test_list_tasks_returns_only_current_users_tasks_newest_first(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    now = datetime.now(timezone.utc)

    older_reel = await Reel(reel_video_id="v1", caption="a reel", url="https://instagram.com/reel/v1").insert()
    newer_reel = await Reel(reel_video_id="v2").insert()
    other_reel = await Reel(reel_video_id="v3").insert()

    await GeneratedTask(
        user_id=user_id,
        reel_id=str(older_reel.id),
        task_type="action_item",
        title="older task",
        details=TaskDetails(description="do the thing"),
        raw_llm_response="{}",
        created_at=now,
    ).insert()
    await GeneratedTask(
        user_id=user_id,
        reel_id=str(newer_reel.id),
        task_type="content_idea",
        title="newer task",
        details=TaskDetails(),
        raw_llm_response="{}",
        created_at=now + timedelta(seconds=1),
    ).insert()
    await GeneratedTask(
        user_id="someone-else",
        reel_id=str(other_reel.id),
        task_type="other",
        title="not mine",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    resp = await client.get("/api/v1/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert [t["title"] for t in body] == ["newer task", "older task"]
    assert body[1]["reel_caption"] == "a reel"
    assert body[1]["reel_url"] == "https://instagram.com/reel/v1"
    assert body[1]["status"] == "not_started"


async def test_list_tasks_requires_auth(client):
    resp = await client.get("/api/v1/tasks")
    assert resp.status_code == 401


async def test_patch_task_status_updates_and_persists(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    task = await GeneratedTask(
        user_id=user_id,
        task_type="other",
        title="a task",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    updated = await GeneratedTask.get(task.id)
    assert updated.status == "in_progress"


async def test_patch_task_status_rejects_another_users_task(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)
    task = await GeneratedTask(
        user_id="someone-else",
        task_type="other",
        title="not mine",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    resp = await client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_patch_task_status_rejects_unknown_task(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)
    resp = await client.patch(
        "/api/v1/tasks/000000000000000000000000",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

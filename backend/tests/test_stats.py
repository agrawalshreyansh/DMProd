from datetime import datetime, timedelta, timezone

import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.push_log import PushLog
from app.models.reel import Reel
from app.models.user_reel import UserReel

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"], resp.json()["user_id"]


async def test_stats_requires_auth(client):
    resp = await client.get("/api/v1/stats")
    assert resp.status_code == 401


async def test_stats_counts_are_exact_against_seeded_fixtures(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    now = datetime.now(timezone.utc)

    succeeded_reel = await Reel(reel_video_id="v1", status="transcribed").insert()
    failed_reel = await Reel(reel_video_id="v2", status="failed").insert()
    processing_reel = await Reel(reel_video_id="v3", status="transcribing").insert()

    await UserReel(
        user_id=user_id, reel_id=str(succeeded_reel.id), sender_ig_id="1", message_id="m1",
        received_at=now,
    ).insert()
    await UserReel(
        user_id=user_id, reel_id=str(failed_reel.id), sender_ig_id="1", message_id="m2",
        received_at=now - timedelta(days=10),
    ).insert()
    await UserReel(
        user_id=user_id, reel_id=str(processing_reel.id), sender_ig_id="1", message_id="m3",
        received_at=now - timedelta(days=40),
    ).insert()
    # Not this user - must never be counted.
    other_reel = await Reel(reel_video_id="v4", status="transcribed").insert()
    await UserReel(
        user_id="someone-else", reel_id=str(other_reel.id), sender_ig_id="9", message_id="m4"
    ).insert()

    task = await GeneratedTask(
        user_id=user_id, reel_id=str(succeeded_reel.id), task_type="action_item", title="t1",
        details=TaskDetails(), raw_llm_response="{}",
    ).insert()
    await GeneratedTask(
        user_id=user_id, reel_id=str(failed_reel.id), task_type="action_item", title="t2",
        details=TaskDetails(), raw_llm_response="{}",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id), integration_type="notion", status="success",
        external_ref_url="https://notion.so/x",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id), integration_type="google_calendar", status="failed",
        error_message="not connected",
    ).insert()

    resp = await client.get("/api/v1/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_reels"] == 3
    assert body["reels_this_week"] == 1
    assert body["reels_this_month"] == 2
    assert body["reels_succeeded"] == 1
    assert body["reels_failed"] == 1
    assert body["reels_processing"] == 1
    assert body["by_task_type"] == [{"label": "action_item", "count": 2}]
    # Only the successful push counts toward a destination breakdown.
    assert body["by_destination"] == [{"label": "notion", "count": 1}]


async def test_stats_destination_breakdown_counts_distinct_tasks_not_push_attempts(
    client, signup_body
):
    # A task re-pushed after a comment-unlock DM reply enriches it (Phase 9)
    # leaves multiple successful PushLog rows behind - the destination
    # breakdown must count it once, not once per push attempt.
    token, user_id = await _signup_and_login(client, signup_body)
    reel = await Reel(reel_video_id="v1", status="transcribed").insert()
    await UserReel(user_id=user_id, reel_id=str(reel.id), sender_ig_id="1", message_id="m1").insert()
    task = await GeneratedTask(
        user_id=user_id, reel_id=str(reel.id), task_type="action_item", title="t1",
        details=TaskDetails(), raw_llm_response="{}",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id), integration_type="notion", status="success",
        external_ref_url="https://notion.so/v1",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id), integration_type="notion", status="success",
        external_ref_url="https://notion.so/v1",
    ).insert()

    resp = await client.get("/api/v1/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["by_destination"] == [{"label": "notion", "count": 1}]


async def test_stats_are_all_zero_with_no_data(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)
    resp = await client.get("/api/v1/stats", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert body["total_reels"] == 0
    assert body["by_task_type"] == []
    assert body["by_destination"] == []

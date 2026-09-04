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


async def test_list_reels_returns_only_current_users_reels_newest_first(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    now = datetime.now(timezone.utc)

    older_reel = await Reel(reel_video_id="v1", caption="older").insert()
    newer_reel = await Reel(reel_video_id="v2", caption="newer").insert()
    other_reel = await Reel(reel_video_id="v3", caption="not mine").insert()

    await UserReel(
        user_id=user_id, reel_id=str(older_reel.id), sender_ig_id="1", message_id="m1", received_at=now
    ).insert()
    await UserReel(
        user_id=user_id,
        reel_id=str(newer_reel.id),
        sender_ig_id="1",
        message_id="m2",
        received_at=now + timedelta(seconds=1),
    ).insert()
    await UserReel(
        user_id="someone-else", reel_id=str(other_reel.id), sender_ig_id="2", message_id="m3"
    ).insert()

    resp = await client.get("/api/v1/reels", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    captions = [r["caption"] for r in resp.json()]
    assert captions == ["newer", "older"]


async def test_list_reels_requires_auth(client):
    resp = await client.get("/api/v1/reels")
    assert resp.status_code == 401


async def test_list_reels_includes_task_and_push_outcome(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    reel = await Reel(reel_video_id="v1", status="transcribed").insert()
    await UserReel(
        user_id=user_id, reel_id=str(reel.id), sender_ig_id="1", message_id="m1",
        task_generation_status="generated",
    ).insert()
    task = await GeneratedTask(
        user_id=user_id,
        reel_id=str(reel.id),
        task_type="action_item",
        title="do the thing",
        details=TaskDetails(),
        raw_llm_response="{}",
        status="in_progress",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id),
        integration_type="notion",
        status="success",
        external_ref_url="https://notion.so/abc",
    ).insert()

    resp = await client.get("/api/v1/reels", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()[0]
    assert row["outcome"] == "in_progress"
    assert row["task"]["title"] == "do the thing"
    assert row["push"] == {"integration_type": "notion", "external_ref_url": "https://notion.so/abc"}


async def test_list_reels_outcome_is_failed_when_pipeline_failed(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    reel = await Reel(reel_video_id="v1", status="failed", error_message="download error").insert()
    await UserReel(user_id=user_id, reel_id=str(reel.id), sender_ig_id="1", message_id="m1").insert()

    resp = await client.get("/api/v1/reels", headers={"Authorization": f"Bearer {token}"})
    row = resp.json()[0]
    assert row["outcome"] == "failed"
    assert row["error_message"] == "download error"
    assert row["task"] is None


async def test_list_reels_outcome_is_processing_before_task_exists(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    reel = await Reel(reel_video_id="v1", status="transcribing").insert()
    await UserReel(user_id=user_id, reel_id=str(reel.id), sender_ig_id="1", message_id="m1").insert()

    resp = await client.get("/api/v1/reels", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()[0]["outcome"] == "processing"


async def test_list_reels_filters_by_task_type_and_status(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    action_reel = await Reel(reel_video_id="v1", status="transcribed").insert()
    idea_reel = await Reel(reel_video_id="v2", status="transcribed").insert()
    await UserReel(user_id=user_id, reel_id=str(action_reel.id), sender_ig_id="1", message_id="m1").insert()
    await UserReel(user_id=user_id, reel_id=str(idea_reel.id), sender_ig_id="1", message_id="m2").insert()
    await GeneratedTask(
        user_id=user_id, reel_id=str(action_reel.id), task_type="action_item", title="a",
        details=TaskDetails(), raw_llm_response="{}", status="completed",
    ).insert()
    await GeneratedTask(
        user_id=user_id, reel_id=str(idea_reel.id), task_type="content_idea", title="b",
        details=TaskDetails(), raw_llm_response="{}", status="not_started",
    ).insert()

    resp = await client.get(
        "/api/v1/reels?task_type=action_item", headers={"Authorization": f"Bearer {token}"}
    )
    assert [r["task"]["title"] for r in resp.json()] == ["a"]

    resp = await client.get(
        "/api/v1/reels?status=completed", headers={"Authorization": f"Bearer {token}"}
    )
    assert [r["task"]["title"] for r in resp.json()] == ["a"]

    resp = await client.get(
        "/api/v1/reels?task_type=other", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.json() == []


async def test_list_reels_filters_by_date_range(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    old_reel = await Reel(reel_video_id="v1").insert()
    recent_reel = await Reel(reel_video_id="v2").insert()
    await UserReel(
        user_id=user_id, reel_id=str(old_reel.id), sender_ig_id="1", message_id="m1",
        received_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    ).insert()
    await UserReel(
        user_id=user_id, reel_id=str(recent_reel.id), sender_ig_id="1", message_id="m2",
        received_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    ).insert()

    resp = await client.get(
        "/api/v1/reels?date_from=2026-03-01", headers={"Authorization": f"Bearer {token}"}
    )
    assert len(resp.json()) == 1

    resp = await client.get(
        "/api/v1/reels?date_to=2026-03-01", headers={"Authorization": f"Bearer {token}"}
    )
    assert len(resp.json()) == 1


async def test_get_reel_detail_returns_full_pipeline_trail(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    reel = await Reel(
        reel_video_id="v1",
        status="transcribed",
        transcript_text="hello world",
        visual_summary="[00:01] a slide",
    ).insert()
    share = await UserReel(
        user_id=user_id, reel_id=str(reel.id), sender_ig_id="1", message_id="m1",
        task_generation_status="generated",
    ).insert()
    task = await GeneratedTask(
        user_id=user_id, reel_id=str(reel.id), task_type="action_item", title="do it",
        details=TaskDetails(description="desc"), raw_llm_response="{}",
    ).insert()
    await PushLog(
        generated_task_id=str(task.id), integration_type="notion", status="success",
        external_ref_url="https://notion.so/abc",
    ).insert()

    resp = await client.get(
        f"/api/v1/reels/{share.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript_text"] == "hello world"
    assert body["visual_summary"] == "[00:01] a slide"
    assert body["title"] == "do it"
    assert body["details"]["description"] == "desc"
    assert len(body["push_logs"]) == 1
    assert body["push_logs"][0]["external_ref_url"] == "https://notion.so/abc"


async def test_get_reel_detail_rejects_another_users_share(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)
    reel = await Reel(reel_video_id="v1").insert()
    share = await UserReel(
        user_id="someone-else", reel_id=str(reel.id), sender_ig_id="1", message_id="m1"
    ).insert()

    resp = await client.get(
        f"/api/v1/reels/{share.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


async def test_get_reel_detail_rejects_unknown_share(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)
    resp = await client.get(
        "/api/v1/reels/000000000000000000000000", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404

from datetime import datetime, timedelta, timezone

import pytest

from app.models.reel import Reel

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"], resp.json()["user_id"]


async def test_list_reels_returns_only_current_users_reels_newest_first(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    now = datetime.now(timezone.utc)

    await Reel(
        user_id=user_id, sender_ig_id="1", message_id="m1", caption="older", received_at=now
    ).insert()
    await Reel(
        user_id=user_id,
        sender_ig_id="1",
        message_id="m2",
        caption="newer",
        received_at=now + timedelta(seconds=1),
    ).insert()
    await Reel(user_id="someone-else", sender_ig_id="2", message_id="m3", caption="not mine").insert()

    resp = await client.get("/api/v1/reels", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    captions = [r["caption"] for r in resp.json()]
    assert captions == ["newer", "older"]


async def test_list_reels_requires_auth(client):
    resp = await client.get("/api/v1/reels")
    assert resp.status_code == 401

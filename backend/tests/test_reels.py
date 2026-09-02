from datetime import datetime, timedelta, timezone

import pytest

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

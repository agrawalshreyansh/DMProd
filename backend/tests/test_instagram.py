from datetime import datetime, timedelta, timezone

import pytest

from app.models.instagram_account import InstagramAccount
from app.models.pending_verification import PendingVerification

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"], resp.json()["user_id"]


async def test_connect_requires_auth(client):
    resp = await client.post("/api/v1/instagram/connect")
    assert resp.status_code == 401


async def test_connect_generates_a_pending_code(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    resp = await client.post(
        "/api/v1/instagram/connect", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["code"]) == 6

    pending = await PendingVerification.find_one(PendingVerification.user_id == user_id)
    assert pending is not None
    assert pending.code == body["code"]


async def test_reconnecting_replaces_the_previous_code(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post("/api/v1/instagram/connect", headers=headers)
    second = await client.post("/api/v1/instagram/connect", headers=headers)

    assert first.json()["code"] != second.json()["code"]
    pending_docs = await PendingVerification.find(PendingVerification.user_id == user_id).to_list()
    assert len(pending_docs) == 1
    assert pending_docs[0].code == second.json()["code"]


async def test_status_and_disconnect(client, signup_body):
    token, user_id = await _signup_and_login(client, signup_body)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/instagram/status", headers=headers)
    assert resp.json() == {"connected": False, "username": None}

    await InstagramAccount(user_id=user_id, ig_user_id="9999", username="realuser").insert()

    resp = await client.get("/api/v1/instagram/status", headers=headers)
    assert resp.json() == {"connected": True, "username": "realuser"}

    resp = await client.delete("/api/v1/instagram", headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/instagram/status", headers=headers)
    assert resp.json() == {"connected": False, "username": None}

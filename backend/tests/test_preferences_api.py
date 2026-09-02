import pytest

pytestmark = pytest.mark.asyncio


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"]


async def test_get_routing_defaults_to_empty(client, signup_body):
    token = await _signup_and_login(client, signup_body)

    resp = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"task_type_routing": {}}


async def test_put_routing_persists_and_returns_it(client, signup_body):
    token = await _signup_and_login(client, signup_body)
    routing = {"action_item": "notion", "content_idea": None}

    resp = await client.put(
        "/api/v1/preferences",
        json={"task_type_routing": routing},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"task_type_routing": routing}

    resp = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.json() == {"task_type_routing": routing}


async def test_put_routing_rejects_unknown_task_type(client, signup_body):
    token = await _signup_and_login(client, signup_body)

    resp = await client.put(
        "/api/v1/preferences",
        json={"task_type_routing": {"not_a_real_type": "notion"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422


async def test_put_routing_rejects_unknown_integration(client, signup_body):
    token = await _signup_and_login(client, signup_body)

    resp = await client.put(
        "/api/v1/preferences",
        json={"task_type_routing": {"action_item": "google_sheet"}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422


async def test_routing_requires_auth(client):
    resp = await client.get("/api/v1/preferences")
    assert resp.status_code == 401

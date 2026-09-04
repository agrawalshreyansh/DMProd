import pytest

pytestmark = pytest.mark.asyncio

DEFAULT_CALENDAR_SCHEDULING = {
    "days_of_week": [0, 1, 2, 3, 4, 5, 6],
    "start_time": "09:00",
    "end_time": "18:00",
    "event_duration_minutes": 30,
    "timezone": "UTC",
}


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"]


async def test_get_preferences_defaults(client, signup_body):
    token = await _signup_and_login(client, signup_body)

    resp = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "task_type_routing": {},
        "calendar_scheduling": DEFAULT_CALENDAR_SCHEDULING,
    }


async def test_put_routing_persists_and_returns_it(client, signup_body):
    token = await _signup_and_login(client, signup_body)
    routing = {"action_item": "notion", "content_idea": None}

    resp = await client.put(
        "/api/v1/preferences",
        json={"task_type_routing": routing},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_type_routing"] == routing
    # calendar_scheduling wasn't included in this PUT — must stay untouched.
    assert resp.json()["calendar_scheduling"] == DEFAULT_CALENDAR_SCHEDULING

    resp = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.json()["task_type_routing"] == routing


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


async def test_put_calendar_scheduling_persists_and_returns_it(client, signup_body):
    token = await _signup_and_login(client, signup_body)
    scheduling = {
        "days_of_week": [0, 1, 2],
        "start_time": "10:00",
        "end_time": "12:30",
        "event_duration_minutes": 45,
        "timezone": "Asia/Kolkata",
    }

    resp = await client.put(
        "/api/v1/preferences",
        json={"calendar_scheduling": scheduling},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["calendar_scheduling"] == scheduling
    # task_type_routing wasn't included in this PUT — must stay untouched.
    assert resp.json()["task_type_routing"] == {}


@pytest.mark.parametrize(
    "override,field_hint",
    [
        ({"days_of_week": []}, "days_of_week"),
        ({"days_of_week": [0, 7]}, "days_of_week"),
        ({"start_time": "not-a-time"}, "start_time"),
        ({"start_time": "18:00", "end_time": "09:00"}, "start_time"),
        ({"event_duration_minutes": 1}, "event_duration_minutes"),
        ({"event_duration_minutes": 1000}, "event_duration_minutes"),
        ({"timezone": "Mars/Cydonia"}, "timezone"),
    ],
)
async def test_put_calendar_scheduling_rejects_invalid_values(
    client, signup_body, override, field_hint
):
    token = await _signup_and_login(client, signup_body)
    scheduling = {**DEFAULT_CALENDAR_SCHEDULING, **override}

    resp = await client.put(
        "/api/v1/preferences",
        json={"calendar_scheduling": scheduling},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422, field_hint


async def test_routing_requires_auth(client):
    resp = await client.get("/api/v1/preferences")
    assert resp.status_code == 401

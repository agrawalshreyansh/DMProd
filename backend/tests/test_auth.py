import pytest

pytestmark = pytest.mark.asyncio


async def test_signup_creates_user_and_returns_token(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == signup_body["email"]
    assert body["access_token"]


async def test_signup_rejects_duplicate_email(client, signup_body):
    await client.post("/api/v1/auth/signup", json=signup_body)
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    assert resp.status_code == 409


async def test_login_succeeds_with_correct_password(client, signup_body):
    await client.post("/api/v1/auth/signup", json=signup_body)
    resp = await client.post("/api/v1/auth/login", json=signup_body)
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_login_rejects_wrong_password(client, signup_body):
    await client.post("/api/v1/auth/signup", json=signup_body)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": signup_body["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_login_rejects_unknown_email(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


async def test_protected_route_rejects_missing_token(client):
    resp = await client.get("/api/v1/settings/gemini-key")
    assert resp.status_code == 401


async def test_protected_route_rejects_invalid_token(client):
    resp = await client.get(
        "/api/v1/settings/gemini-key",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


async def test_protected_route_accepts_valid_token(client, signup_body):
    signup = await client.post("/api/v1/auth/signup", json=signup_body)
    token = signup.json()["access_token"]
    resp = await client.get(
        "/api/v1/settings/gemini-key",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

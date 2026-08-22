import pytest

from app.models.user_credential import UserCredential
from app.services.credentials import CredentialService

pytestmark = pytest.mark.asyncio


async def test_set_then_get_round_trips(app):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-real-key"})
    result = await CredentialService.get("user-1", "gemini")
    assert result == {"api_key": "sk-real-key"}


async def test_set_twice_upserts_not_duplicates(app):
    await CredentialService.set("user-1", "gemini", {"api_key": "first"})
    await CredentialService.set("user-1", "gemini", {"api_key": "second"})

    docs = await UserCredential.find(
        UserCredential.user_id == "user-1", UserCredential.provider == "gemini"
    ).to_list()
    assert len(docs) == 1
    assert (await CredentialService.get("user-1", "gemini"))["api_key"] == "second"


async def test_get_missing_provider_returns_none(app):
    assert await CredentialService.get("user-1", "gemini") is None


async def test_secret_is_encrypted_at_rest(app):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-real-key"})
    doc = await UserCredential.find_one(
        UserCredential.user_id == "user-1", UserCredential.provider == "gemini"
    )
    assert "sk-real-key" not in doc.encrypted_secret


async def test_delete_removes_credential(app):
    await CredentialService.set("user-1", "gemini", {"api_key": "sk-real-key"})
    assert await CredentialService.delete("user-1", "gemini") is True
    assert await CredentialService.get("user-1", "gemini") is None
    assert await CredentialService.delete("user-1", "gemini") is False


async def test_settings_endpoint_round_trip(client, signup_body):
    signup = await client.post("/api/v1/auth/signup", json=signup_body)
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    before = await client.get("/api/v1/settings/gemini-key", headers=headers)
    assert before.json() == {"connected": False, "masked_key": None}

    put = await client.put(
        "/api/v1/settings/gemini-key", json={"api_key": "sk-real-key"}, headers=headers
    )
    assert put.status_code == 200
    assert put.json() == {"connected": True, "masked_key": "••••-key"}

    after = await client.get("/api/v1/settings/gemini-key", headers=headers)
    assert after.json() == {"connected": True, "masked_key": "••••-key"}

    put_again = await client.put(
        "/api/v1/settings/gemini-key", json={"api_key": "sk-second-key"}, headers=headers
    )
    assert put_again.json() == {"connected": True, "masked_key": "••••-key"}
    docs = await UserCredential.find(UserCredential.provider == "gemini").to_list()
    assert len(docs) == 1

    doc = await UserCredential.find_one(UserCredential.provider == "gemini")
    assert "sk-real-key" not in doc.encrypted_secret

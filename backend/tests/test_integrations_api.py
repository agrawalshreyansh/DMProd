import httpx
import pytest
from notion_client.errors import APIResponseError

from app.api import integrations as integrations_module
from app.models.integration import Integration
from app.services.credentials import CredentialService

pytestmark = pytest.mark.asyncio


def _fake_async_client(database=None, raise_error=None, calls=None):
    class _Databases:
        async def retrieve(self, database_id):
            if calls is not None:
                calls.append(database_id)
            if raise_error is not None:
                raise raise_error
            return database

    class _Fake:
        def __init__(self, auth):
            self.auth = auth
            self.databases = _Databases()

        async def aclose(self):
            pass

    return _Fake


async def _signup_and_login(client, signup_body):
    resp = await client.post("/api/v1/auth/signup", json=signup_body)
    return resp.json()["access_token"], resp.json()["user_id"]


async def test_connect_notion_stores_credential_and_integration(client, signup_body, monkeypatch):
    token, user_id = await _signup_and_login(client, signup_body)
    database = {
        "title": [{"plain_text": "My Tasks"}],
        "data_sources": [{"id": "ds-1", "name": "My Tasks"}],
    }
    monkeypatch.setattr(integrations_module, "AsyncClient", _fake_async_client(database=database))

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"connected": True, "database_id": "db-1", "database_title": "My Tasks"}

    secret = await CredentialService.get(user_id, "notion")
    assert secret == {"token": "secret-token"}

    integration = await Integration.find_one(
        Integration.user_id == user_id, Integration.type == "notion"
    )
    assert integration is not None
    assert integration.target_config == {
        "database_id": "db-1",
        "data_source_id": "ds-1",
        "database_title": "My Tasks",
    }


async def test_connect_notion_rejects_invalid_token_or_database(client, signup_body, monkeypatch):
    token, user_id = await _signup_and_login(client, signup_body)
    error = APIResponseError(
        code="object_not_found",
        status=404,
        message="not found",
        headers=httpx.Headers(),
        raw_body_text="{}",
    )
    monkeypatch.setattr(integrations_module, "AsyncClient", _fake_async_client(raise_error=error))

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "bad-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert await CredentialService.get(user_id, "notion") is None


async def test_connect_notion_rejects_database_with_no_data_source(client, signup_body, monkeypatch):
    token, user_id = await _signup_and_login(client, signup_body)
    database = {"title": [], "data_sources": []}
    monkeypatch.setattr(integrations_module, "AsyncClient", _fake_async_client(database=database))

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert await CredentialService.get(user_id, "notion") is None


async def test_get_notion_status_not_connected_by_default(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)

    resp = await client.get(
        "/api/v1/integrations/notion", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "database_id": None, "database_title": None}


async def test_get_notion_status_requires_auth(client):
    resp = await client.get("/api/v1/integrations/notion")
    assert resp.status_code == 401


async def test_disconnect_notion_removes_credential_and_integration(client, signup_body, monkeypatch):
    token, user_id = await _signup_and_login(client, signup_body)
    database = {"title": [{"plain_text": "My Tasks"}], "data_sources": [{"id": "ds-1"}]}
    monkeypatch.setattr(integrations_module, "AsyncClient", _fake_async_client(database=database))
    await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.delete(
        "/api/v1/integrations/notion", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    assert await CredentialService.get(user_id, "notion") is None
    assert (
        await Integration.find_one(Integration.user_id == user_id, Integration.type == "notion")
        is None
    )

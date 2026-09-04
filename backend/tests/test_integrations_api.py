import httpx
import pytest
from notion_client.errors import APIResponseError

from app.api import integrations as integrations_module
from app.models.integration import Integration
from app.services.credentials import CredentialService
from app.services.google_oauth import GoogleOAuthError

pytestmark = pytest.mark.asyncio


def _fake_httpx_client(status_code=200, json_data=None):
    class _Response:
        def __init__(self):
            self.status_code = status_code
            self._json = json_data or {}

        def json(self):
            return self._json

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, **kwargs):
            return _Response()

    return _Client


def _fake_async_client(
    database=None,
    raise_error=None,
    calls=None,
    data_source_properties=None,
    update_raise_error=None,
):
    class _Databases:
        async def retrieve(self, database_id):
            if calls is not None:
                calls.setdefault("database_retrieve", []).append(database_id)
            if raise_error is not None:
                raise raise_error
            return database

    class _DataSources:
        async def retrieve(self, data_source_id):
            if calls is not None:
                calls.setdefault("data_source_retrieve", []).append(data_source_id)
            return {"properties": data_source_properties or {}}

        async def update(self, data_source_id, **kwargs):
            if calls is not None:
                calls.setdefault("data_source_update", []).append((data_source_id, kwargs))
            if update_raise_error is not None:
                raise update_raise_error

    class _Fake:
        def __init__(self, auth):
            self.auth = auth
            self.databases = _Databases()
            self.data_sources = _DataSources()

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


async def test_connect_notion_creates_missing_columns_on_a_fresh_database(
    client, signup_body, monkeypatch
):
    token, _ = await _signup_and_login(client, signup_body)
    database = {"title": [{"plain_text": "My Tasks"}], "data_sources": [{"id": "ds-1"}]}
    calls = {}
    monkeypatch.setattr(
        integrations_module,
        "AsyncClient",
        _fake_async_client(database=database, data_source_properties={}, calls=calls),
    )

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data_source_id, update_kwargs = calls["data_source_update"][0]
    assert data_source_id == "ds-1"
    added = update_kwargs["properties"]
    assert set(added.keys()) == {"Due Date", "Status", "Task Type"}
    assert added["Due Date"] == {"date": {}}
    assert {o["name"] for o in added["Status"]["select"]["options"]} == {
        "Not started",
        "In progress",
        "Completed",
    }


async def test_connect_notion_skips_columns_that_already_exist(client, signup_body, monkeypatch):
    token, _ = await _signup_and_login(client, signup_body)
    database = {"title": [{"plain_text": "My Tasks"}], "data_sources": [{"id": "ds-1"}]}
    calls = {}
    monkeypatch.setattr(
        integrations_module,
        "AsyncClient",
        _fake_async_client(
            database=database,
            data_source_properties={
                "Name": {"type": "title"},
                "Deadline": {"type": "date"},
                "Status": {"type": "status"},
            },
            calls=calls,
        ),
    )

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    _, update_kwargs = calls["data_source_update"][0]
    assert set(update_kwargs["properties"].keys()) == {"Task Type"}


async def test_connect_notion_fails_cleanly_when_schema_setup_fails(
    client, signup_body, monkeypatch
):
    token, user_id = await _signup_and_login(client, signup_body)
    database = {"title": [{"plain_text": "My Tasks"}], "data_sources": [{"id": "ds-1"}]}
    error = APIResponseError(
        code="restricted_resource",
        status=403,
        message="no write access",
        headers=httpx.Headers(),
        raw_body_text="{}",
    )
    monkeypatch.setattr(
        integrations_module,
        "AsyncClient",
        _fake_async_client(database=database, data_source_properties={}, update_raise_error=error),
    )

    resp = await client.post(
        "/api/v1/integrations/notion",
        json={"token": "secret-token", "database_id": "db-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert await CredentialService.get(user_id, "notion") is None
    assert (
        await Integration.find_one(Integration.user_id == user_id, Integration.type == "notion")
        is None
    )


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


async def test_google_calendar_connect_returns_authorize_url(client, signup_body, monkeypatch):
    token, _ = await _signup_and_login(client, signup_body)
    monkeypatch.setattr(integrations_module, "is_configured", lambda: True)
    monkeypatch.setattr(
        integrations_module, "build_authorize_url", lambda state: f"https://accounts.google.com/auth?state={state}"
    )

    resp = await client.get(
        "/api/v1/integrations/google-calendar/connect",
        params={"state": "csrf-abc"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"authorize_url": "https://accounts.google.com/auth?state=csrf-abc"}


async def test_google_calendar_connect_fails_when_not_configured(client, signup_body, monkeypatch):
    token, _ = await _signup_and_login(client, signup_body)
    monkeypatch.setattr(integrations_module, "is_configured", lambda: False)

    resp = await client.get(
        "/api/v1/integrations/google-calendar/connect",
        params={"state": "csrf-abc"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 503


async def test_google_calendar_callback_stores_credential_and_integration(
    client, signup_body, monkeypatch
):
    token, user_id = await _signup_and_login(client, signup_body)

    async def _fake_exchange(code):
        assert code == "auth-code-1"
        return {"access_token": "at-1", "refresh_token": "rt-1", "expires_at": 9999999999.0}

    monkeypatch.setattr(integrations_module, "exchange_code", _fake_exchange)
    monkeypatch.setattr(
        integrations_module.httpx,
        "AsyncClient",
        _fake_httpx_client(200, {"summary": "My Calendar"}),
    )

    resp = await client.post(
        "/api/v1/integrations/google-calendar/callback",
        json={"code": "auth-code-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"connected": True, "calendar_summary": "My Calendar"}

    secret = await CredentialService.get(user_id, "google")
    assert secret == {"access_token": "at-1", "refresh_token": "rt-1", "expires_at": 9999999999.0}

    integration = await Integration.find_one(
        Integration.user_id == user_id, Integration.type == "google_calendar"
    )
    assert integration is not None
    assert integration.target_config == {"calendar_id": "primary", "calendar_summary": "My Calendar"}


async def test_google_calendar_callback_rejects_invalid_code(client, signup_body, monkeypatch):
    token, user_id = await _signup_and_login(client, signup_body)

    async def _fake_exchange(code):
        raise GoogleOAuthError("Google rejected the authorization code")

    monkeypatch.setattr(integrations_module, "exchange_code", _fake_exchange)

    resp = await client.post(
        "/api/v1/integrations/google-calendar/callback",
        json={"code": "bad-code"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400
    assert await CredentialService.get(user_id, "google") is None


async def test_get_google_calendar_status_not_connected_by_default(client, signup_body):
    token, _ = await _signup_and_login(client, signup_body)

    resp = await client.get(
        "/api/v1/integrations/google-calendar", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "calendar_summary": None}


async def test_disconnect_google_calendar_removes_credential_and_integration(
    client, signup_body, monkeypatch
):
    token, user_id = await _signup_and_login(client, signup_body)

    async def _fake_exchange(code):
        return {"access_token": "at-1", "refresh_token": "rt-1", "expires_at": 9999999999.0}

    monkeypatch.setattr(integrations_module, "exchange_code", _fake_exchange)
    monkeypatch.setattr(
        integrations_module.httpx, "AsyncClient", _fake_httpx_client(200, {"summary": "Cal"})
    )
    await client.post(
        "/api/v1/integrations/google-calendar/callback",
        json={"code": "auth-code-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.delete(
        "/api/v1/integrations/google-calendar", headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 200
    assert resp.json()["connected"] is False
    assert await CredentialService.get(user_id, "google") is None
    assert (
        await Integration.find_one(
            Integration.user_id == user_id, Integration.type == "google_calendar"
        )
        is None
    )

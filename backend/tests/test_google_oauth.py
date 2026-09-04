from urllib.parse import parse_qs, urlparse

import pytest

from app.services import google_oauth as google_oauth_module
from app.services.credentials import CredentialService
from app.services.google_oauth import (
    GoogleOAuthError,
    build_authorize_url,
    exchange_code,
    get_valid_access_token,
    is_configured,
)

pytestmark = pytest.mark.asyncio


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = str(self._json)

    def json(self):
        return self._json


def _fake_async_client(responses=None, calls=None):
    responses = list(responses or [])

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, **kwargs):
            if calls is not None:
                calls.append({"url": url, "data": data})
            return responses.pop(0)

    return _Client


@pytest.fixture(autouse=True)
def google_credentials(monkeypatch):
    monkeypatch.setattr(google_oauth_module.settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(google_oauth_module.settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr(google_oauth_module.settings, "cors_origin", "http://localhost:3000")


async def test_is_configured_true_when_both_set():
    assert is_configured() is True


async def test_is_configured_false_when_missing(monkeypatch):
    monkeypatch.setattr(google_oauth_module.settings, "google_client_id", "")
    assert is_configured() is False


async def test_build_authorize_url_includes_required_params():
    url = build_authorize_url("state-123")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert qs["client_id"] == ["test-client-id"]
    assert qs["redirect_uri"] == ["http://localhost:3000/api/google-calendar/callback"]
    assert qs["response_type"] == ["code"]
    assert qs["access_type"] == ["offline"]
    assert qs["prompt"] == ["consent"]
    assert qs["state"] == ["state-123"]
    assert "calendar.events" in qs["scope"][0]


async def test_exchange_code_posts_expected_params_and_returns_tokens(monkeypatch):
    calls = []
    response = _FakeResponse(
        200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 3600}
    )
    monkeypatch.setattr(
        google_oauth_module.httpx, "AsyncClient", _fake_async_client([response], calls)
    )

    tokens = await exchange_code("auth-code")

    assert tokens["access_token"] == "at-1"
    assert tokens["refresh_token"] == "rt-1"
    assert tokens["expires_at"] > 0

    posted = calls[0]["data"]
    assert posted["code"] == "auth-code"
    assert posted["grant_type"] == "authorization_code"
    assert posted["redirect_uri"] == "http://localhost:3000/api/google-calendar/callback"


async def test_exchange_code_raises_when_no_refresh_token(monkeypatch):
    response = _FakeResponse(200, {"access_token": "at-1", "expires_in": 3600})
    monkeypatch.setattr(google_oauth_module.httpx, "AsyncClient", _fake_async_client([response]))

    with pytest.raises(GoogleOAuthError, match="refresh token"):
        await exchange_code("auth-code")


async def test_exchange_code_raises_on_non_200(monkeypatch):
    response = _FakeResponse(400, {"error": "invalid_grant"})
    monkeypatch.setattr(google_oauth_module.httpx, "AsyncClient", _fake_async_client([response]))

    with pytest.raises(GoogleOAuthError, match="rejected"):
        await exchange_code("bad-code")


async def test_get_valid_access_token_returns_none_when_not_connected(app):
    assert await get_valid_access_token("user-1") is None


async def test_get_valid_access_token_returns_cached_token_when_not_expired(app, monkeypatch):
    await CredentialService.set(
        "user-1",
        "google",
        {"access_token": "at-cached", "refresh_token": "rt-1", "expires_at": 9999999999},
    )
    calls = []
    monkeypatch.setattr(google_oauth_module.httpx, "AsyncClient", _fake_async_client([], calls))

    token = await get_valid_access_token("user-1")

    assert token == "at-cached"
    assert calls == []


async def test_get_valid_access_token_refreshes_when_expired_and_persists(app, monkeypatch):
    await CredentialService.set(
        "user-1",
        "google",
        {"access_token": "at-old", "refresh_token": "rt-1", "expires_at": 1.0},
    )
    response = _FakeResponse(200, {"access_token": "at-new", "expires_in": 3600})
    monkeypatch.setattr(google_oauth_module.httpx, "AsyncClient", _fake_async_client([response]))

    token = await get_valid_access_token("user-1")

    assert token == "at-new"
    persisted = await CredentialService.get("user-1", "google")
    assert persisted["access_token"] == "at-new"
    assert persisted["refresh_token"] == "rt-1"  # preserved, Google doesn't resend it


async def test_get_valid_access_token_raises_when_refresh_fails(app, monkeypatch):
    await CredentialService.set(
        "user-1",
        "google",
        {"access_token": "at-old", "refresh_token": "rt-1", "expires_at": 1.0},
    )
    response = _FakeResponse(400, {"error": "invalid_grant"})
    monkeypatch.setattr(google_oauth_module.httpx, "AsyncClient", _fake_async_client([response]))

    with pytest.raises(GoogleOAuthError, match="refresh failed"):
        await get_valid_access_token("user-1")

import pytest

from app.services import instagram_private as ip_module
from app.services.instagram_private import InstagramPrivateError, comment_on_reel, follow_user

pytestmark = pytest.mark.asyncio


class _FakeClient:
    def __init__(self, login_error=None, calls=None):
        self.login_error = login_error
        self.calls = calls if calls is not None else []
        self.logged_in = False

    def load_settings(self, path):
        self.calls.append(("load_settings", path))

    def login_by_sessionid(self, sessionid):
        self.calls.append(("login_by_sessionid", sessionid))
        if self.login_error is not None:
            raise self.login_error
        self.logged_in = True
        return True

    def dump_settings(self, path):
        self.calls.append(("dump_settings", path))

    def user_id_from_username(self, username):
        self.calls.append(("user_id_from_username", username))
        return f"uid-{username}"

    def user_follow(self, user_id):
        self.calls.append(("user_follow", user_id))
        return True

    def media_pk_from_url(self, url):
        self.calls.append(("media_pk_from_url", url))
        return "pk-123"

    def media_id(self, pk):
        self.calls.append(("media_id", pk))
        return f"media-{pk}"

    def media_comment(self, media_id, text):
        self.calls.append(("media_comment", media_id, text))
        return object()


@pytest.fixture(autouse=True)
def reset_client_singleton(monkeypatch, tmp_path):
    # Each test gets a fresh lazy-init and a session file that doesn't
    # exist yet, so load_settings/login always run predictably.
    monkeypatch.setattr(ip_module, "_client", None)
    monkeypatch.setattr(ip_module, "SESSION_FILE", tmp_path / "session.json")
    monkeypatch.setattr(ip_module.settings, "instagram_session_id", "test-session-id")


async def test_follow_user_logs_in_and_follows(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(ip_module, "Client", lambda: fake)

    await follow_user("someuser")

    assert ("login_by_sessionid", "test-session-id") in fake.calls
    assert ("user_id_from_username", "someuser") in fake.calls
    assert ("user_follow", "uid-someuser") in fake.calls


async def test_comment_on_reel_resolves_media_and_comments(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(ip_module, "Client", lambda: fake)

    await comment_on_reel("https://www.instagram.com/reel/abc/", "YES")

    assert ("media_pk_from_url", "https://www.instagram.com/reel/abc/") in fake.calls
    assert ("media_id", "pk-123") in fake.calls
    assert ("media_comment", "media-pk-123", "YES") in fake.calls


async def test_client_is_reused_across_calls_not_relogged_in(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(ip_module, "Client", lambda: fake)

    await follow_user("a")
    await follow_user("b")

    login_calls = [c for c in fake.calls if c[0] == "login_by_sessionid"]
    assert len(login_calls) == 1


async def test_raises_when_session_id_not_configured(monkeypatch):
    monkeypatch.setattr(ip_module.settings, "instagram_session_id", "")

    with pytest.raises(InstagramPrivateError, match="not configured"):
        await follow_user("someuser")


async def test_raises_when_login_fails(monkeypatch):
    fake = _FakeClient(login_error=RuntimeError("bad session"))
    monkeypatch.setattr(ip_module, "Client", lambda: fake)

    with pytest.raises(InstagramPrivateError, match="login failed"):
        await follow_user("someuser")


async def test_raises_when_follow_action_fails(monkeypatch):
    fake = _FakeClient()

    def _raise(*a, **k):
        raise RuntimeError("rate limited")

    fake.user_follow = _raise
    monkeypatch.setattr(ip_module, "Client", lambda: fake)

    with pytest.raises(InstagramPrivateError, match="failed to follow"):
        await follow_user("someuser")

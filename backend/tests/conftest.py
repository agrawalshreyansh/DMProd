import os

from cryptography.fernet import Fernet

os.environ.setdefault("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("META_APP_SECRET", "test-meta-app-secret")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("INSTAGRAM_BOT_ACCESS_TOKEN", "test-bot-access-token")

import fakeredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import app.queue as queue_module
from app.db import init_db
from app.main import create_app
from app.models import document_models


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """No real Redis in tests — every test gets its own fake queue."""
    monkeypatch.setattr(queue_module, "_connection", fakeredis.FakeStrictRedis())


@pytest_asyncio.fixture
async def app():
    client = AsyncMongoMockClient()
    await init_db(client)
    yield create_app()
    for model in document_models:
        await model.get_motor_collection().drop()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def signup_body():
    return {"email": "alex@example.com", "password": "correct-horse-battery-staple"}


@pytest.fixture
def instagram_webhook_payload():
    # Shape confirmed against a real Meta delivery during manual testing.
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "17841400000000000",
                "time": 1700000000,
                "messaging": [
                    {
                        "sender": {"id": "1234567890"},
                        "recipient": {"id": "17841400000000000"},
                        "timestamp": 1700000000123,
                        "message": {
                            "mid": "aWdfZAG1faXRlbToxOgN...",
                            "attachments": [
                                {
                                    "type": "ig_reel",
                                    "payload": {
                                        "reel_video_id": "17871182922633701",
                                        "title": "A reel about something",
                                        "url": "https://www.instagram.com/reel/abc123/",
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def sign_payload(raw_body: bytes, secret: str = "test-meta-app-secret") -> str:
    import hashlib
    import hmac

    return "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

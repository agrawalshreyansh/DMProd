import os

from cryptography.fernet import Fernet

os.environ.setdefault("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.db import init_db
from app.main import create_app
from app.models import document_models


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

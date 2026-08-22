from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import document_models


async def init_db(client: AsyncIOMotorClient | None = None) -> AsyncIOMotorClient:
    """Connect Beanie to Mongo. Pass a client (e.g. mongomock) in tests."""
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=client[settings.mongo_db_name],
        document_models=document_models,
    )
    return client

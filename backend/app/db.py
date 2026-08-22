import certifi
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models import document_models


def _is_tls_uri(uri: str) -> bool:
    # ponytail: string-match heuristic, not a full URI parser. Covers the
    # two real cases (Atlas `mongodb+srv://`, or an explicit tls=true query
    # param) — extend if a TLS variant that doesn't match either shows up.
    return uri.startswith("mongodb+srv://") or "tls=true" in uri or "ssl=true" in uri


async def init_db(client: AsyncIOMotorClient | None = None) -> AsyncIOMotorClient:
    """Connect Beanie to Mongo. Pass a client (e.g. mongomock) in tests."""
    if client is None:
        # macOS python.org builds don't use the system CA store, so TLS to
        # Atlas fails with CERTIFICATE_VERIFY_FAILED unless pointed at
        # certifi's bundle explicitly. Only relevant for TLS connections —
        # tlsCAFile errors out if passed on a non-TLS (plain local) URI.
        extra = {"tlsCAFile": certifi.where()} if _is_tls_uri(settings.mongo_uri) else {}
        client = AsyncIOMotorClient(settings.mongo_uri, **extra)
    await init_beanie(
        database=client[settings.mongo_db_name],
        document_models=document_models,
    )
    return client

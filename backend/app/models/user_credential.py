from datetime import datetime, timezone
from typing import Any, Literal

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

Provider = Literal["gemini", "instagram", "notion", "google"]


class UserCredential(Document):
    """Central store for every secret the app holds on a user's behalf.

    One document per (user_id, provider). `encrypted_secret` is an opaque,
    Fernet-encrypted JSON blob whose shape is provider-specific — decided by
    the provider's own code, not by this model. Never add per-provider
    plaintext fields here (e.g. access_token/refresh_token columns); that
    reintroduces the per-provider sprawl this collection exists to avoid.
    """

    user_id: str
    provider: Provider
    encrypted_secret: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "user_credentials"
        indexes = [
            IndexModel([("user_id", 1), ("provider", 1)], unique=True),
        ]

from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class InstagramAccount(Document):
    """Identity/verification link between a dashboard User and their real
    Instagram account. No token here — that lives in user_credentials via
    CredentialService; identity and secrets are two different concerns.
    """

    user_id: str
    ig_user_id: str
    username: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "instagram_accounts"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("ig_user_id", 1)], unique=True),
        ]

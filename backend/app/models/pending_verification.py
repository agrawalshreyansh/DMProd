from datetime import datetime

from beanie import Document
from pymongo import IndexModel


class PendingVerification(Document):
    """A one-time code a user must DM to the bot's Instagram account to
    prove they control it. TTL-indexed so expired codes clean themselves up
    (the webhook handler also checks `expires_at` itself — Mongo's TTL sweep
    only runs periodically, so it can't be relied on for correctness).
    """

    user_id: str
    code: str
    expires_at: datetime

    class Settings:
        name = "pending_verifications"
        indexes = [
            IndexModel([("user_id", 1)], unique=True),
            IndexModel([("code", 1)], unique=True),
            IndexModel([("expires_at", 1)], expireAfterSeconds=0),
        ]

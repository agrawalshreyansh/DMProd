from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Reel(Document):
    """A reel a verified user shared with the bot, resolved to their account.

    `message_id` carries a unique index because Meta can redeliver the same
    webhook event — this is what makes storing a reel idempotent.
    """

    user_id: str
    sender_ig_id: str
    message_id: str
    reel_video_id: str | None = None
    url: str | None = None
    caption: str | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reels"
        indexes = [
            IndexModel([("message_id", 1)], unique=True),
            IndexModel([("user_id", 1), ("received_at", -1)]),
        ]

from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Reel(Document):
    """Shared reel content — one document per distinct `reel_video_id`,
    regardless of how many users shared it. Per-user share events live in
    `UserReel`; this doc holds only what the processing pipeline produces.
    """

    reel_video_id: str | None = None
    url: str | None = None
    caption: str | None = None
    status: str = "received"
    error_message: str | None = None
    transcript_text: str | None = None
    transcript_language: str | None = None
    transcript_duration_seconds: float | None = None
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reels"
        indexes = [
            IndexModel(
                [("reel_video_id", 1)],
                unique=True,
                partialFilterExpression={"reel_video_id": {"$exists": True}},
            ),
        ]

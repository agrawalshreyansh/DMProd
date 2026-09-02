from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class UserReel(Document):
    """One document per (user, reel) pair — a user has shared this reel with
    the bot at least once. The reel's own content/pipeline state lives on
    `Reel` (`reel_id`), shared across every user who shared the same reel.

    `message_id` carries a unique index because Meta can redeliver the same
    webhook event — this is what makes storing a share idempotent.
    `(user_id, reel_id)` is unique too: the same user re-sharing a reel
    they've already shared doesn't need a second row.

    `task_generation_status`/`task_generation_error` track whether Phase 7's
    Gemini call succeeded for this (user, reel) — system state, not the
    user's own todo progress (that's `GeneratedTask.status`).
    """

    user_id: str
    reel_id: str
    sender_ig_id: str
    message_id: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_generation_status: str = "pending"
    task_generation_error: str | None = None

    class Settings:
        name = "user_reels"
        indexes = [
            IndexModel([("message_id", 1)], unique=True),
            IndexModel([("user_id", 1), ("reel_id", 1)], unique=True),
            IndexModel([("user_id", 1), ("received_at", -1)]),
        ]

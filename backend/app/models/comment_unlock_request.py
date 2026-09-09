from datetime import datetime, timezone
from typing import Any, Literal

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

CommentUnlockRequestStatus = Literal["pending", "fulfilled", "expired"]


class CommentUnlockRequest(Document):
    """One outstanding "waiting on the creator's DM reply" record per reel
    (not per user — a Reel is shared content). `creator_username` is
    denormalized from `Reel` for display/debugging."""

    reel_id: str
    creator_username: str | None = None
    keyword: str
    status: CommentUnlockRequestStatus = "pending"
    commented_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    followed_at: datetime | None = None
    fulfilled_at: datetime | None = None
    reply_text: str | None = None
    # The fulfilling DM's Meta message id — guards against Meta's webhook
    # redelivering the same message and getting matched to a *different*
    # (by then still-pending) request the second time around.
    reply_message_id: str | None = None
    # The raw DM payload that fulfilled this request — kept for debugging
    # the many CTA/button shapes IG and DM-automation tools send (some of
    # which carry the real link at an unpredictable depth, or not at all).
    reply_raw: dict[str, Any] | None = None

    class Settings:
        name = "comment_unlock_requests"
        indexes = [
            IndexModel([("reel_id", 1)], unique=True),
            IndexModel([("status", 1), ("commented_at", 1)]),
        ]

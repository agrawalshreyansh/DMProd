from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel

CommentUnlockStatus = Literal["pending", "commented", "fulfilled", "expired", "failed"]
VisualProcessingStatus = Literal["pending", "processing", "done", "failed", "skipped"]


class VisualEvent(BaseModel):
    """Embedded, one per surviving keyframe after dedup — raw structured
    output from Phase 13's Gemini vision call, kept for audit (same spirit
    as `GeneratedTask.raw_llm_response`). `Reel.visual_summary` is the
    merged text actually fed to Phase 7's prompt, not this list directly.

    For a carousel post (`Reel.media_type == "carousel"`) there are no
    video timestamps — `timestamp_seconds` carries the 1-based slide number
    instead."""

    timestamp_seconds: float
    description: str
    on_screen_text: str | None = None


class Reel(Document):
    """Shared reel content — one document per distinct `reel_video_id`,
    regardless of how many users shared it. Per-user share events live in
    `UserReel`; this doc holds only what the processing pipeline produces.
    """

    reel_video_id: str | None = None
    url: str | None = None
    caption: str | None = None
    # "reel" (video → audio → transcript → keyframes) or "carousel" (a feed
    # post of images shared in a DM → all slide images → one vision pass, no
    # audio). Downstream terminal status is "transcribed" for both so the
    # enqueue/webhook logic needs no per-type branch.
    media_type: Literal["reel", "carousel"] = "reel"
    status: str = "received"
    error_message: str | None = None
    transcript_text: str | None = None
    transcript_language: str | None = None
    transcript_duration_seconds: float | None = None
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Phase 9 (comment-to-unlock) — creator_username is from yt-dlp, used to
    # follow/unfollow via instagrapi; comment_unlock_status is None for the
    # (vast majority of) reels that never mention a comment-to-DM trigger,
    # distinct from `status` above which only tracks download/transcribe.
    creator_username: str | None = None
    comment_unlock_keyword: str | None = None
    comment_unlock_status: CommentUnlockStatus | None = None
    # Phase 13 (visual analysis) — separate from `status` above: a visual
    # failure must never block the download/audio/transcribe flow that
    # already works without it. `visual_events`/`visual_summary` are
    # computed once per Reel (shared content) and reused by every user's
    # Phase 7 task-gen call for it.
    visual_events: list[VisualEvent] = Field(default_factory=list)
    visual_summary: str | None = None
    visual_processing_status: VisualProcessingStatus | None = None

    class Settings:
        name = "reels"
        indexes = [
            IndexModel(
                [("reel_video_id", 1)],
                unique=True,
                partialFilterExpression={"reel_video_id": {"$exists": True}},
            ),
        ]

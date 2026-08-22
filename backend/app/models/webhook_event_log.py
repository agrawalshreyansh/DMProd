from datetime import datetime, timezone
from typing import Any

from beanie import Document
from pydantic import Field


class WebhookEventLog(Document):
    """Raw Instagram webhook payloads, kept for debugging this phase.

    Not meant to be a permanent audit table — Phase 3+ introduces the real
    Reel/ProcessingJob tracking. This can be trimmed/dropped once that
    lands, or repurposed for retry/replay if that turns out useful.
    """

    raw_payload: dict[str, Any]
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "webhook_event_logs"

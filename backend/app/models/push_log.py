from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

PushStatus = Literal["success", "failed"]


class PushLog(Document):
    """One row per push attempt, success or failure — the audit trail behind
    a dashboard "view in Notion" link and behind surfacing why a push failed."""

    generated_task_id: str
    integration_type: str
    status: PushStatus
    external_ref_url: str | None = None
    error_message: str | None = None
    pushed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "push_logs"
        indexes = [
            IndexModel([("generated_task_id", 1)]),
        ]

from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel

TaskType = Literal["content_idea", "action_item", "event_reminder", "resource_reference", "other"]
TaskStatus = Literal["not_started", "in_progress", "completed"]


class TaskDetails(BaseModel):
    """Embedded, not a Document — one flexible shape covering all task
    types rather than five rigid per-type schemas."""

    description: str | None = None
    location: str | None = None
    link: str | None = None
    key_points: list[str] = Field(default_factory=list)


class GeneratedTask(Document):
    """A structured task/content-idea extracted from a reel (or, from Phase
    9 onward, created manually). `status` is the user's own todo state —
    distinct from `UserReel.task_generation_status`, which tracks whether
    generation itself succeeded, not what the user has done with the result.
    """

    user_id: str
    reel_id: str | None = None
    source: Literal["reel", "manual"] = "reel"
    task_type: TaskType
    title: str
    details: TaskDetails
    due_date: datetime | None = None
    status: TaskStatus = "not_started"
    raw_llm_response: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "generated_tasks"
        indexes = [
            IndexModel(
                [("user_id", 1), ("reel_id", 1)],
                unique=True,
                partialFilterExpression={"reel_id": {"$exists": True}},
            ),
            IndexModel([("user_id", 1), ("created_at", -1)]),
        ]

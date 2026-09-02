from typing import Literal

from beanie import Document, Indexed
from pydantic import Field

# ponytail: "notion" is the only routable destination (Phase 8 scope). Add
# "google_calendar"/"google_sheet" here once those integrations exist.
RoutingTarget = Literal["notion"]


class Preference(Document):
    user_id: Indexed(str, unique=True)
    # task_type -> integration to auto-push to, or None to leave dashboard-only.
    # Keyed by GeneratedTask.TaskType string rather than the Literal itself so
    # an unset task_type just isn't a dict key, no need to pre-seed all five.
    task_type_routing: dict[str, RoutingTarget | None] = Field(default_factory=dict)

    class Settings:
        name = "preferences"

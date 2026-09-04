from typing import Literal

from beanie import Document, Indexed
from pydantic import BaseModel, Field

# ponytail: add "google_sheet" here once that integration exists.
RoutingTarget = Literal["notion", "google_calendar"]


class CalendarSchedulingPreference(BaseModel):
    """When push_to_gcal is free to place a reminder. Defaults are
    permissive (any day, 9-6, UTC) so a user who never visits Preferences
    still gets something reasonable rather than nothing scheduling at all."""

    # Python's date.weekday() convention: 0=Monday .. 6=Sunday.
    days_of_week: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    start_time: str = "09:00"  # "HH:MM", 24h, interpreted in `timezone` below
    end_time: str = "18:00"
    event_duration_minutes: int = 30
    timezone: str = "UTC"  # IANA name, e.g. "Asia/Kolkata" — validated in the API layer


class Preference(Document):
    user_id: Indexed(str, unique=True)
    # task_type -> integration to auto-push to, or None to leave dashboard-only.
    # Keyed by GeneratedTask.TaskType string rather than the Literal itself so
    # an unset task_type just isn't a dict key, no need to pre-seed all five.
    task_type_routing: dict[str, RoutingTarget | None] = Field(default_factory=dict)
    calendar_scheduling: CalendarSchedulingPreference = Field(
        default_factory=CalendarSchedulingPreference
    )

    class Settings:
        name = "preferences"

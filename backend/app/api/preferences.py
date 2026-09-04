from datetime import time as time_cls
from zoneinfo import available_timezones

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.generated_task import TaskType
from app.models.preference import CalendarSchedulingPreference, Preference, RoutingTarget
from app.models.user import User

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])

VALID_TASK_TYPES: set[str] = set(TaskType.__args__)
VALID_ROUTING_TARGETS: set[str] = set(RoutingTarget.__args__)
VALID_TIMEZONES = available_timezones()


class PreferenceBody(BaseModel):
    task_type_routing: dict[str, str | None]
    calendar_scheduling: CalendarSchedulingPreference


class PreferenceUpdate(BaseModel):
    # Both optional and independent — omit one to leave it untouched (the
    # routing table and calendar-scheduling form save separately).
    task_type_routing: dict[str, str | None] | None = None
    calendar_scheduling: CalendarSchedulingPreference | None = None


async def _get_or_create(user_id: str) -> Preference:
    preference = await Preference.find_one(Preference.user_id == user_id)
    if preference is None:
        preference = Preference(user_id=user_id)
        await preference.insert()
    return preference


def _validate_routing(routing: dict[str, str | None]) -> None:
    for task_type, target in routing.items():
        if task_type not in VALID_TASK_TYPES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown task_type: {task_type}"
            )
        if target is not None and target not in VALID_ROUTING_TARGETS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown integration: {target}"
            )


def _validate_calendar_scheduling(prefs: CalendarSchedulingPreference) -> None:
    if not prefs.days_of_week or any(d not in range(7) for d in prefs.days_of_week):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "days_of_week must be a non-empty list of integers 0 (Monday) to 6 (Sunday).",
        )
    try:
        start = time_cls.fromisoformat(prefs.start_time)
        end = time_cls.fromisoformat(prefs.end_time)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "start_time/end_time must be HH:MM."
        )
    if start >= end:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "start_time must be before end_time."
        )
    if not (5 <= prefs.event_duration_minutes <= 480):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "event_duration_minutes must be between 5 and 480.",
        )
    if prefs.timezone not in VALID_TIMEZONES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown timezone: {prefs.timezone}"
        )


@router.get("", response_model=PreferenceBody)
async def get_preferences(user: User = Depends(get_current_user)) -> PreferenceBody:
    preference = await _get_or_create(str(user.id))
    return PreferenceBody(
        task_type_routing=preference.task_type_routing,
        calendar_scheduling=preference.calendar_scheduling,
    )


@router.put("", response_model=PreferenceBody)
async def set_preferences(
    body: PreferenceUpdate, user: User = Depends(get_current_user)
) -> PreferenceBody:
    if body.task_type_routing is not None:
        _validate_routing(body.task_type_routing)
    if body.calendar_scheduling is not None:
        _validate_calendar_scheduling(body.calendar_scheduling)

    preference = await _get_or_create(str(user.id))
    if body.task_type_routing is not None:
        preference.task_type_routing = body.task_type_routing
    if body.calendar_scheduling is not None:
        preference.calendar_scheduling = body.calendar_scheduling
    await preference.save()

    return PreferenceBody(
        task_type_routing=preference.task_type_routing,
        calendar_scheduling=preference.calendar_scheduling,
    )

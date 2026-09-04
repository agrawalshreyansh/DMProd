from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.models.generated_task import GeneratedTask
from app.models.integration import Integration
from app.models.preference import CalendarSchedulingPreference, Preference
from app.services.calendar_scheduling import (
    BusyInterval,
    candidate_days,
    compute_date_range,
    find_free_slot,
)
from app.services.google_oauth import GoogleOAuthError, get_valid_access_token

CALENDAR_URL = "https://www.googleapis.com/calendar/v3"


class GcalPushError(Exception):
    pass


def _description(task: GeneratedTask) -> str | None:
    lines = []
    if task.details.description:
        lines.append(task.details.description)
    if task.details.location:
        lines.append(f"Location: {task.details.location}")
    if task.details.link:
        lines.append(f"Link: {task.details.link}")
    lines.extend(f"- {point}" for point in task.details.key_points)
    return "\n".join(lines) or None


async def _fetch_busy_intervals(
    access_token: str, calendar_id: str, time_min: datetime, time_max: datetime
) -> list[BusyInterval]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CALENDAR_URL}/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "items": [{"id": calendar_id}],
            },
        )
    if resp.status_code >= 400:
        raise GcalPushError(f"Google Calendar availability check failed: {resp.text}")

    busy_raw = resp.json().get("calendars", {}).get(calendar_id, {}).get("busy", [])
    return [
        BusyInterval(start=datetime.fromisoformat(b["start"]), end=datetime.fromisoformat(b["end"]))
        for b in busy_raw
    ]


def _resolve_timezone(prefs: CalendarSchedulingPreference) -> ZoneInfo:
    try:
        return ZoneInfo(prefs.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


async def _pick_slot(
    task: GeneratedTask, prefs: CalendarSchedulingPreference, access_token: str, calendar_id: str
) -> tuple[datetime, datetime]:
    """The (start, end) datetime to schedule `task`'s reminder at — the
    first slot free on a preferred day within [today, due_date] (or just
    today, with no due_date), or the preferred window's opening slot on the
    last candidate day if every checked day is fully booked. Never fails
    to return a slot — an over-booked reminder beats a silently dropped one."""
    tz = _resolve_timezone(prefs)
    start_time = time.fromisoformat(prefs.start_time)
    end_time = time.fromisoformat(prefs.end_time)

    today = datetime.now(tz).date()
    due = task.due_date.date() if task.due_date else None
    earliest, latest = compute_date_range(due, task.reminder_lead_days, today)
    days = candidate_days(earliest, latest, prefs.days_of_week)

    # One freebusy call covering every candidate day, rather than one per
    # day — find_free_slot below only compares a given day's window against
    # the intervals that actually overlap it.
    time_min = datetime.combine(days[0], start_time, tzinfo=tz)
    time_max = datetime.combine(days[-1], end_time, tzinfo=tz)
    busy = await _fetch_busy_intervals(access_token, calendar_id, time_min, time_max)

    for day in days:
        slot_start = find_free_slot(
            day, tz, busy, start_time, end_time, prefs.event_duration_minutes
        )
        if slot_start is not None:
            return slot_start, slot_start + timedelta(minutes=prefs.event_duration_minutes)

    fallback_start = datetime.combine(days[-1], start_time, tzinfo=tz)
    return fallback_start, fallback_start + timedelta(minutes=prefs.event_duration_minutes)


async def push_to_gcal(
    task: GeneratedTask, integration: Integration, existing_event_id: str | None = None
) -> tuple[str, str]:
    """Creates an event for `task` on the user's configured Google
    Calendar, timed within their scheduling preferences (days of week +
    time window) and checked against their real calendar availability via
    freeBusy so it doesn't land on top of an existing event — including a
    previously-pushed task, since that already exists as a real event by
    the time this runs.

    When `existing_event_id` is given (a prior successful push for this
    task, per `push_task`'s PushLog lookup), updates that event's
    summary/description in place instead of creating a second one — and
    deliberately skips re-picking a slot: the existing event already
    occupies its own time on the calendar, so a freeBusy check would see
    it as "busy" and relocate it for no reason.

    Returns (url, event_id); the id is what a later re-push needs to
    update this same event again. Raises GcalPushError on any failure —
    caller (push_task) is the one that logs it to `push_logs`."""
    try:
        access_token = await get_valid_access_token(task.user_id)
    except GoogleOAuthError as exc:
        raise GcalPushError(str(exc)) from exc
    if access_token is None:
        raise GcalPushError("Google Calendar is not connected")

    calendar_id = integration.target_config.get("calendar_id", "primary")

    if existing_event_id is not None:
        event_body = {"summary": task.title, "description": _description(task)}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{CALENDAR_URL}/calendars/{calendar_id}/events/{existing_event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=event_body,
                )
            if resp.status_code >= 400:
                raise GcalPushError(f"Google Calendar API error: {resp.text}")
        except httpx.HTTPError as exc:
            raise GcalPushError(str(exc)) from exc

        event = resp.json()
        url = event.get("htmlLink")
        if not url:
            raise GcalPushError("Google Calendar did not return an event link")
        return url, existing_event_id

    preference = await Preference.find_one(Preference.user_id == task.user_id)
    prefs = preference.calendar_scheduling if preference else CalendarSchedulingPreference()

    try:
        slot_start, slot_end = await _pick_slot(task, prefs, access_token, calendar_id)
    except GcalPushError:
        raise
    except httpx.HTTPError as exc:
        raise GcalPushError(str(exc)) from exc

    event_body = {
        "summary": task.title,
        "description": _description(task),
        "start": {"dateTime": slot_start.isoformat(), "timeZone": prefs.timezone},
        "end": {"dateTime": slot_end.isoformat(), "timeZone": prefs.timezone},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CALENDAR_URL}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=event_body,
            )
        if resp.status_code >= 400:
            raise GcalPushError(f"Google Calendar API error: {resp.text}")
    except httpx.HTTPError as exc:
        raise GcalPushError(str(exc)) from exc

    event = resp.json()
    url = event.get("htmlLink")
    event_id = event.get("id")
    if not url or not event_id:
        raise GcalPushError("Google Calendar did not return an event link/id")
    return url, event_id

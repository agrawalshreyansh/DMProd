from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo


@dataclass
class BusyInterval:
    start: datetime
    end: datetime


def compute_date_range(
    due_date: date | None, reminder_lead_days: int, today: date
) -> tuple[date, date]:
    """(earliest, latest) date to search for a slot, inclusive of both.
    Never earlier than `today` (a lead time landing in the past just means
    "as soon as possible" instead of literally scheduling into the past),
    never later than due_date itself (a reminder after the deadline is
    useless)."""
    if due_date is None:
        return today, today
    target = due_date - timedelta(days=reminder_lead_days)
    earliest = max(target, today)
    latest = max(due_date, earliest)
    return earliest, latest


def candidate_days(earliest: date, latest: date, days_of_week: list[int]) -> list[date]:
    """Every date in [earliest, latest] whose weekday is in days_of_week
    (Monday=0..Sunday=6), oldest first. Falls back to `[latest]` when
    nothing in range matches — scheduling on a non-preferred day beats
    never scheduling at all."""
    days = []
    current = earliest
    while current <= latest:
        if current.weekday() in days_of_week:
            days.append(current)
        current += timedelta(days=1)
    return days or [latest]


def find_free_slot(
    day: date,
    tz: tzinfo,
    busy_intervals: list[BusyInterval],
    start_time: time,
    end_time: time,
    duration_minutes: int,
    step_minutes: int = 15,
) -> datetime | None:
    """First slot of `duration_minutes` within [start_time, end_time) on
    `day` (interpreted in `tz`) that doesn't overlap any busy_intervals.
    None if the whole window is booked."""
    window_start = datetime.combine(day, start_time, tzinfo=tz)
    window_end = datetime.combine(day, end_time, tzinfo=tz)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    candidate = window_start
    while candidate + duration <= window_end:
        candidate_end = candidate + duration
        if not any(
            candidate < busy.end and candidate_end > busy.start for busy in busy_intervals
        ):
            return candidate
        candidate += step
    return None

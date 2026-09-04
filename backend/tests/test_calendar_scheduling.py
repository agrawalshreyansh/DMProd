from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.calendar_scheduling import (
    BusyInterval,
    candidate_days,
    compute_date_range,
    find_free_slot,
)

UTC = ZoneInfo("UTC")


def test_compute_date_range_with_no_due_date_returns_today_only():
    today = date(2026, 9, 10)
    assert compute_date_range(None, reminder_lead_days=0, today=today) == (today, today)


def test_compute_date_range_subtracts_lead_days_from_due_date():
    due = date(2026, 9, 23)
    today = date(2026, 9, 1)
    earliest, latest = compute_date_range(due, reminder_lead_days=3, today=today)
    assert earliest == date(2026, 9, 20)
    assert latest == due


def test_compute_date_range_never_starts_before_today():
    due = date(2026, 9, 3)
    today = date(2026, 9, 2)
    # lead_days would push target before today
    earliest, latest = compute_date_range(due, reminder_lead_days=5, today=today)
    assert earliest == today
    assert latest == due


def test_compute_date_range_same_day_reminder_when_lead_days_zero():
    due = date(2026, 9, 23)
    today = date(2026, 9, 1)
    earliest, latest = compute_date_range(due, reminder_lead_days=0, today=today)
    assert earliest == due
    assert latest == due


def test_candidate_days_filters_to_allowed_weekdays():
    # 2026-09-07 is a Monday
    earliest = date(2026, 9, 7)
    latest = date(2026, 9, 13)
    days = candidate_days(earliest, latest, days_of_week=[0, 2, 4])  # Mon/Wed/Fri
    assert days == [date(2026, 9, 7), date(2026, 9, 9), date(2026, 9, 11)]


def test_candidate_days_falls_back_to_latest_when_nothing_matches():
    earliest = date(2026, 9, 7)  # Monday
    latest = date(2026, 9, 7)
    days = candidate_days(earliest, latest, days_of_week=[5, 6])  # weekend only
    assert days == [latest]


def test_find_free_slot_returns_window_start_when_nothing_busy():
    day = date(2026, 9, 10)
    slot = find_free_slot(day, UTC, [], time(9, 0), time(18, 0), duration_minutes=30)
    assert slot == datetime(2026, 9, 10, 9, 0, tzinfo=UTC)


def test_find_free_slot_skips_past_a_busy_interval():
    day = date(2026, 9, 10)
    busy = [
        BusyInterval(
            start=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            end=datetime(2026, 9, 10, 9, 30, tzinfo=UTC),
        )
    ]
    slot = find_free_slot(day, UTC, busy, time(9, 0), time(18, 0), duration_minutes=30)
    assert slot == datetime(2026, 9, 10, 9, 30, tzinfo=UTC)


def test_find_free_slot_returns_none_when_window_fully_booked():
    day = date(2026, 9, 10)
    busy = [
        BusyInterval(
            start=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
            end=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        )
    ]
    slot = find_free_slot(day, UTC, busy, time(9, 0), time(18, 0), duration_minutes=30)
    assert slot is None


def test_find_free_slot_respects_duration_not_just_a_free_instant():
    # A 20-minute gap can't fit a 30-minute event.
    day = date(2026, 9, 10)
    busy = [
        BusyInterval(
            start=datetime(2026, 9, 10, 9, 20, tzinfo=UTC),
            end=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        )
    ]
    slot = find_free_slot(day, UTC, busy, time(9, 0), time(18, 0), duration_minutes=30)
    assert slot is None


def test_find_free_slot_partial_overlap_at_window_edges_is_still_busy():
    day = date(2026, 9, 10)
    # Busy interval starts before the window and ends inside it.
    busy = [
        BusyInterval(
            start=datetime(2026, 9, 10, 8, 45, tzinfo=UTC),
            end=datetime(2026, 9, 10, 9, 15, tzinfo=UTC),
        )
    ]
    slot = find_free_slot(day, UTC, busy, time(9, 0), time(18, 0), duration_minutes=30)
    assert slot == datetime(2026, 9, 10, 9, 15, tzinfo=UTC)

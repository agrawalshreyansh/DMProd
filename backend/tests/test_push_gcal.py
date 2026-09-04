from datetime import datetime, timedelta, timezone

import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.integration import Integration
from app.models.preference import CalendarSchedulingPreference, Preference
from app.services.credentials import CredentialService
from app.workers import push_gcal as push_gcal_module
from app.workers.push_gcal import GcalPushError, push_to_gcal

pytestmark = pytest.mark.asyncio


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or str(self._json)

    def json(self):
        return self._json


def _fake_async_client(responses, calls=None):
    """`responses` is a list consumed in order: first freeBusy, then
    events.insert (or however many `.post()` calls push_to_gcal makes)."""
    queue = list(responses)

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None, **kwargs):
            if calls is not None:
                calls.append({"method": "post", "url": url, "headers": headers, "json": json})
            return queue.pop(0)

        async def patch(self, url, headers=None, json=None, **kwargs):
            if calls is not None:
                calls.append({"method": "patch", "url": url, "headers": headers, "json": json})
            return queue.pop(0)

    return _Client


async def _make_task(**overrides):
    fields = dict(
        user_id="user-1",
        task_type="event_reminder",
        title="Apply for the internship",
        details=TaskDetails(description="Submit before the deadline", key_points=["Bring resume"]),
        raw_llm_response="{}",
    )
    fields.update(overrides)
    return await GeneratedTask(**fields).insert()


def _integration():
    return Integration(
        user_id="user-1", type="google_calendar", target_config={"calendar_id": "primary"}
    )


async def _connect_google():
    await CredentialService.set(
        "user-1",
        "google",
        {"access_token": "at-1", "refresh_token": "rt-1", "expires_at": 9999999999.0},
    )


async def test_push_to_gcal_schedules_within_default_window_when_no_preference_set(
    app, monkeypatch
):
    await _connect_google()
    # 2026-09-10 is a Thursday; no due_date -> "today" (frozen via due_date-free task,
    # scheduling logic uses datetime.now(tz).date(), so just assert shape not exact date).
    task = await _make_task(due_date=None)
    calls = []
    freebusy_resp = _FakeResponse(200, {"calendars": {"primary": {"busy": []}}})
    event_resp = _FakeResponse(200, {"htmlLink": "https://calendar.google.com/event?eid=abc", "id": "event-abc"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp], calls)
    )

    url, event_id = await push_to_gcal(task, _integration())

    assert url == "https://calendar.google.com/event?eid=abc"
    assert event_id == "event-abc"
    assert calls[0]["url"] == "https://www.googleapis.com/calendar/v3/freeBusy"
    event_call = calls[1]
    assert event_call["url"] == "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    assert event_call["json"]["summary"] == task.title
    assert event_call["json"]["start"]["dateTime"].endswith("09:00:00+00:00")
    assert event_call["json"]["start"]["timeZone"] == "UTC"
    end_dt = event_call["json"]["end"]["dateTime"]
    assert end_dt.endswith("09:30:00+00:00")  # default 30-minute duration


async def test_push_to_gcal_skips_busy_slot_and_uses_next_free_one(app, monkeypatch):
    await _connect_google()
    task = await _make_task(due_date=None)
    calls = []
    freebusy_resp = _FakeResponse(
        200,
        {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": datetime.now(timezone.utc).strftime("%Y-%m-%dT09:00:00+00:00"),
                            "end": datetime.now(timezone.utc).strftime("%Y-%m-%dT09:30:00+00:00"),
                        }
                    ]
                }
            }
        },
    )
    event_resp = _FakeResponse(200, {"htmlLink": "https://calendar.google.com/event?eid=xyz", "id": "event-xyz"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp], calls)
    )

    await push_to_gcal(task, _integration())

    assert calls[1]["json"]["start"]["dateTime"].endswith("09:30:00+00:00")


async def test_push_to_gcal_uses_calendar_scheduling_preference(app, monkeypatch):
    await _connect_google()
    await Preference(
        user_id="user-1",
        calendar_scheduling=CalendarSchedulingPreference(
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            start_time="14:00",
            end_time="16:00",
            event_duration_minutes=60,
            timezone="Asia/Kolkata",
        ),
    ).insert()
    task = await _make_task(due_date=None)
    calls = []
    freebusy_resp = _FakeResponse(200, {"calendars": {"primary": {"busy": []}}})
    event_resp = _FakeResponse(200, {"htmlLink": "https://calendar.google.com/event?eid=abc", "id": "event-abc"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp], calls)
    )

    await push_to_gcal(task, _integration())

    event_json = calls[1]["json"]
    assert event_json["start"]["dateTime"].endswith("14:00:00+05:30")
    assert event_json["start"]["timeZone"] == "Asia/Kolkata"
    assert event_json["end"]["dateTime"].endswith("15:00:00+05:30")  # 60-minute duration


async def test_push_to_gcal_schedules_days_before_due_date_per_reminder_lead_days(
    app, monkeypatch
):
    await _connect_google()
    # Far enough out that "today" (whenever the suite runs) never catches up
    # to the earliest candidate date and changes the expected slot.
    due = (datetime.now(timezone.utc) + timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    task = await _make_task(due_date=due, reminder_lead_days=3)
    calls = []
    freebusy_resp = _FakeResponse(200, {"calendars": {"primary": {"busy": []}}})
    event_resp = _FakeResponse(200, {"htmlLink": "https://calendar.google.com/event?eid=abc", "id": "event-abc"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp], calls)
    )

    await push_to_gcal(task, _integration())

    expected_date = (due - timedelta(days=3)).date().isoformat()
    assert calls[1]["json"]["start"]["dateTime"].startswith(f"{expected_date}T09:00:00")


async def test_push_to_gcal_falls_back_to_window_open_when_fully_booked(app, monkeypatch):
    await _connect_google()
    due = (datetime.now(timezone.utc) + timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    due_str = due.date().isoformat()
    task = await _make_task(due_date=due, reminder_lead_days=0)
    calls = []
    freebusy_resp = _FakeResponse(
        200,
        {
            "calendars": {
                "primary": {
                    "busy": [{"start": f"{due_str}T09:00:00+00:00", "end": f"{due_str}T18:00:00+00:00"}]
                }
            }
        },
    )
    event_resp = _FakeResponse(200, {"htmlLink": "https://calendar.google.com/event?eid=full", "id": "event-full"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp], calls)
    )

    url, event_id = await push_to_gcal(task, _integration())

    assert url == "https://calendar.google.com/event?eid=full"
    assert event_id == "event-full"
    assert calls[1]["json"]["start"]["dateTime"] == f"{due_str}T09:00:00+00:00"


async def test_push_to_gcal_updates_existing_event_instead_of_creating_one(app, monkeypatch):
    # Phase 9: enriching a task with a creator's DM reply re-pushes it —
    # this must update the event it already made, in its original slot,
    # not create a duplicate or relocate it based on its own busy time.
    await _connect_google()
    task = await _make_task(due_date=None)
    calls = []
    patch_resp = _FakeResponse(
        200, {"htmlLink": "https://calendar.google.com/event?eid=abc", "id": "event-abc"}
    )
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([patch_resp], calls)
    )

    url, event_id = await push_to_gcal(task, _integration(), existing_event_id="event-abc")

    assert url == "https://calendar.google.com/event?eid=abc"
    assert event_id == "event-abc"
    assert len(calls) == 1  # no freeBusy call, no re-picked slot
    assert calls[0]["method"] == "patch"
    assert calls[0]["url"] == "https://www.googleapis.com/calendar/v3/calendars/primary/events/event-abc"
    assert calls[0]["json"] == {"summary": task.title, "description": "Submit before the deadline\n- Bring resume"}


async def test_push_to_gcal_raises_when_not_connected(app):
    task = await _make_task()

    with pytest.raises(GcalPushError, match="not connected"):
        await push_to_gcal(task, _integration())


async def test_push_to_gcal_raises_on_freebusy_error(app, monkeypatch):
    await _connect_google()
    task = await _make_task(due_date=None)
    freebusy_resp = _FakeResponse(403, {"error": "insufficient permission"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp])
    )

    with pytest.raises(GcalPushError, match="availability check failed"):
        await push_to_gcal(task, _integration())


async def test_push_to_gcal_raises_on_event_create_error(app, monkeypatch):
    await _connect_google()
    task = await _make_task(due_date=None)
    freebusy_resp = _FakeResponse(200, {"calendars": {"primary": {"busy": []}}})
    event_resp = _FakeResponse(500, {"error": "backend error"})
    monkeypatch.setattr(
        push_gcal_module.httpx, "AsyncClient", _fake_async_client([freebusy_resp, event_resp])
    )

    with pytest.raises(GcalPushError, match="backend error"):
        await push_to_gcal(task, _integration())

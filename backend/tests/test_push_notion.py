from datetime import datetime, timezone

import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.integration import Integration
from app.services.credentials import CredentialService
from app.workers import push_notion as push_notion_module
from app.workers.push_notion import NotionPushError, push_to_notion

pytestmark = pytest.mark.asyncio


def _fake_async_client(data_source=None, page=None, raise_error=None, calls=None):
    class _DataSources:
        async def retrieve(self, data_source_id):
            if calls is not None:
                calls.setdefault("data_source_id", []).append(data_source_id)
            return data_source

    class _Pages:
        async def create(self, **kwargs):
            if calls is not None:
                calls.setdefault("pages_create", []).append(kwargs)
            if raise_error is not None:
                raise raise_error
            return page

    class _Fake:
        def __init__(self, auth):
            self.auth = auth
            self.data_sources = _DataSources()
            self.pages = _Pages()

        async def aclose(self):
            pass

    return _Fake


async def _make_task(**overrides):
    fields = dict(
        user_id="user-1",
        task_type="action_item",
        title="Batch-cook the pasta sauce",
        details=TaskDetails(description="Make it Sunday", key_points=["3 ingredients"]),
        raw_llm_response="{}",
    )
    fields.update(overrides)
    return await GeneratedTask(**fields).insert()


def _integration():
    return Integration(user_id="user-1", type="notion", target_config={"data_source_id": "ds-1"})


async def test_push_to_notion_creates_page_with_title_and_body(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Status": {"type": "status"}}}
    page = {"url": "https://notion.so/abc123"}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page=page, calls=calls),
    )

    url = await push_to_notion(task, _integration())

    assert url == "https://notion.so/abc123"
    create_kwargs = calls["pages_create"][0]
    assert create_kwargs["parent"] == {"type": "data_source_id", "data_source_id": "ds-1"}
    assert create_kwargs["properties"]["Name"]["title"][0]["text"]["content"] == task.title
    assert "Status" not in create_kwargs["properties"]
    # description paragraph + one key_point bullet
    assert len(create_kwargs["children"]) == 2


async def test_push_to_notion_sets_date_property_when_column_exists(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(due_date=datetime(2026, 3, 5, tzinfo=timezone.utc))
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Due": {"type": "date"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    properties = calls["pages_create"][0]["properties"]
    assert properties["Due"] == {"date": {"start": "2026-03-05"}}


async def test_push_to_notion_skips_date_when_no_date_column(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(due_date=datetime(2026, 3, 5, tzinfo=timezone.utc))
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    properties = calls["pages_create"][0]["properties"]
    assert list(properties.keys()) == ["Name"]


async def test_push_to_notion_raises_when_not_connected(app):
    task = await _make_task()

    with pytest.raises(NotionPushError, match="not connected"):
        await push_to_notion(task, _integration())


async def test_push_to_notion_raises_when_no_title_property(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    data_source = {"properties": {"Status": {"type": "status"}}}
    monkeypatch.setattr(
        push_notion_module, "AsyncClient", _fake_async_client(data_source=data_source)
    )

    with pytest.raises(NotionPushError, match="title property"):
        await push_to_notion(task, _integration())


async def test_push_to_notion_wraps_api_errors(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    data_source = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, raise_error=RuntimeError("rate limited")),
    )

    with pytest.raises(NotionPushError, match="rate limited"):
        await push_to_notion(task, _integration())

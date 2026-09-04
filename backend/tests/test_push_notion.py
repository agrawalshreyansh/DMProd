from datetime import datetime, timezone

import pytest

from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.integration import Integration
from app.services.credentials import CredentialService
from app.workers import push_notion as push_notion_module
from app.workers.push_notion import NotionPushError, push_to_notion

pytestmark = pytest.mark.asyncio


def _fake_async_client(
    data_source=None, page=None, raise_error=None, calls=None, existing_children=None
):
    class _DataSources:
        async def retrieve(self, data_source_id):
            if calls is not None:
                calls.setdefault("data_source_id", []).append(data_source_id)
            return data_source

        async def update(self, data_source_id, properties):
            if calls is not None:
                calls.setdefault("data_source_update", []).append(
                    {"data_source_id": data_source_id, "properties": properties}
                )

    class _Pages:
        async def create(self, **kwargs):
            if calls is not None:
                calls.setdefault("pages_create", []).append(kwargs)
            if raise_error is not None:
                raise raise_error
            return page

        async def update(self, **kwargs):
            if calls is not None:
                calls.setdefault("pages_update", []).append(kwargs)
            if raise_error is not None:
                raise raise_error
            return page

    class _BlocksChildren:
        async def list(self, block_id):
            if calls is not None:
                calls.setdefault("blocks_list", []).append(block_id)
            return {"results": existing_children or []}

        async def append(self, block_id, children):
            if calls is not None:
                calls.setdefault("blocks_append", []).append({"block_id": block_id, "children": children})

    class _Blocks:
        def __init__(self):
            self.children = _BlocksChildren()

        async def delete(self, block_id):
            if calls is not None:
                calls.setdefault("blocks_delete", []).append(block_id)

    class _Fake:
        def __init__(self, auth):
            self.auth = auth
            self.data_sources = _DataSources()
            self.pages = _Pages()
            self.blocks = _Blocks()

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
    page = {"url": "https://notion.so/abc123", "id": "page-abc123"}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page=page, calls=calls),
    )

    url, page_id = await push_to_notion(task, _integration())

    assert url == "https://notion.so/abc123"
    assert page_id == "page-abc123"
    create_kwargs = calls["pages_create"][0]
    assert create_kwargs["parent"] == {"type": "data_source_id", "data_source_id": "ds-1"}
    assert create_kwargs["properties"]["Name"]["title"][0]["text"]["content"] == task.title
    assert "Status" not in create_kwargs["properties"]
    # description paragraph + one key_point bullet
    assert len(create_kwargs["children"]) == 2
    # also mirrored into a property so it shows in the database's default
    # grid view, not just inside the page body
    assert (
        create_kwargs["properties"]["Description"]["rich_text"][0]["text"]["content"]
        == task.details.description
    )


async def test_push_to_notion_creates_missing_description_column(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(
            data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls
        ),
    )

    await push_to_notion(task, _integration())

    assert calls["data_source_update"][0] == {
        "data_source_id": "ds-1",
        "properties": {"Description": {"rich_text": {}}},
    }


async def test_push_to_notion_skips_description_property_when_column_is_wrong_type(app, monkeypatch):
    # A pre-existing "Description" column of some other type must never
    # receive a rich_text-shaped value - same rule as Status above.
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Description": {"type": "select"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(
            data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls
        ),
    )

    await push_to_notion(task, _integration())

    assert "data_source_update" not in calls  # never touches the existing column
    assert "Description" not in calls["pages_create"][0]["properties"]


async def test_push_to_notion_truncates_description_property_to_notion_limit(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(details=TaskDetails(description="x" * 3000))
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Description": {"type": "rich_text"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(
            data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls
        ),
    )

    await push_to_notion(task, _integration())

    content = calls["pages_create"][0]["properties"]["Description"]["rich_text"][0]["text"]["content"]
    assert len(content) == push_notion_module.DESCRIPTION_PROPERTY_MAX_LEN


async def test_push_to_notion_skips_description_property_when_no_description(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(details=TaskDetails())
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(
            data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls
        ),
    )

    await push_to_notion(task, _integration())

    assert "data_source_update" not in calls  # never creates the column for nothing
    assert "Description" not in calls["pages_create"][0]["properties"]


async def test_push_to_notion_sets_date_property_when_column_exists(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(due_date=datetime(2026, 3, 5, tzinfo=timezone.utc))
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Due": {"type": "date"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    properties = calls["pages_create"][0]["properties"]
    assert properties["Due"] == {"date": {"start": "2026-03-05"}}


async def test_push_to_notion_sets_status_and_task_type_when_select_columns_exist(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(task_type="event_reminder")
    task.status = "in_progress"
    calls = {}
    data_source = {
        "properties": {
            "Name": {"type": "title"},
            "Status": {"type": "select"},
            "Task Type": {"type": "select"},
        }
    }
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    properties = calls["pages_create"][0]["properties"]
    assert properties["Status"] == {"select": {"name": "In progress"}}
    assert properties["Task Type"] == {"select": {"name": "Event reminder"}}


async def test_push_to_notion_skips_status_when_column_is_wrong_type(app, monkeypatch):
    # A pre-existing "Status" column of Notion's native `status` type (not
    # `select`) must never receive a select-shaped value — Notion would
    # reject the mismatched payload.
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}, "Status": {"type": "status"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    assert "Status" not in calls["pages_create"][0]["properties"]


async def test_push_to_notion_skips_date_when_no_date_column(app, monkeypatch):
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task(due_date=datetime(2026, 3, 5, tzinfo=timezone.utc))
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}}}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(data_source=data_source, page={"url": "https://notion.so/x", "id": "page-x"}, calls=calls),
    )

    await push_to_notion(task, _integration())

    properties = calls["pages_create"][0]["properties"]
    assert "Due" not in properties and "Date" not in properties


async def test_push_to_notion_updates_existing_page_instead_of_creating_one(app, monkeypatch):
    # Phase 9: enriching a task with a creator's DM reply re-pushes it —
    # this must update the page it already made, not create a duplicate.
    await CredentialService.set("user-1", "notion", {"token": "secret-token"})
    task = await _make_task()
    calls = {}
    data_source = {"properties": {"Name": {"type": "title"}}}
    page = {"url": "https://notion.so/abc123", "id": "page-abc123"}
    monkeypatch.setattr(
        push_notion_module,
        "AsyncClient",
        _fake_async_client(
            data_source=data_source,
            page=page,
            calls=calls,
            existing_children=[{"id": "old-block-1"}, {"id": "old-block-2"}],
        ),
    )

    url, page_id = await push_to_notion(task, _integration(), existing_page_id="page-abc123")

    assert url == "https://notion.so/abc123"
    assert page_id == "page-abc123"
    assert "pages_create" not in calls  # never creates a second page
    assert calls["pages_update"][0]["page_id"] == "page-abc123"
    assert calls["blocks_delete"] == ["old-block-1", "old-block-2"]
    assert calls["blocks_append"][0]["block_id"] == "page-abc123"


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

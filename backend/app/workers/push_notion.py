from notion_client import AsyncClient

from app.models.generated_task import GeneratedTask
from app.models.integration import Integration
from app.services.credentials import CredentialService

# Labels for the "Status"/"Task Type" select columns connect_notion offers to
# auto-create. Shared with app/api/integrations.py so the options it creates
# match exactly what push_to_notion writes into them.
STATUS_LABELS: dict[str, str] = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "completed": "Completed",
}
TASK_TYPE_LABELS: dict[str, str] = {
    "content_idea": "Content idea",
    "action_item": "Action item",
    "event_reminder": "Event reminder",
    "resource_reference": "Resource reference",
    "other": "Other",
}


class NotionPushError(Exception):
    pass


def _find_property(properties: dict, prop_type: str) -> str | None:
    for name, schema in properties.items():
        if schema.get("type") == prop_type:
            return name
    return None


def _named_select_property(properties: dict, name: str) -> str | None:
    """Only matches if `name` exists AND is actually a select column — never
    writes a select value into some other property type that happens to
    share the name (e.g. a pre-existing "Status" of Notion's native `status`
    type, which needs a differently-shaped value)."""
    return name if properties.get(name, {}).get("type") == "select" else None


# Notion truncates a single rich_text content string beyond this length -
# the property is a grid-view-visible preview, the page body (_build_children,
# no length limit applied there) stays the full text either way.
DESCRIPTION_PROPERTY_MAX_LEN = 2000


async def _ensure_description_property(client: AsyncClient, data_source_id: str, properties: dict) -> str | None:
    """The task's description/key_points already land in the page body
    (_build_children), but a database's default grid view only shows
    *properties* as columns - body content is invisible until a page is
    opened. Mirrors app.api.integrations._ensure_task_schema's create-if-
    missing pattern, just run here instead so it also self-heals for a
    database connected before this property existed, not only fresh ones.
    Returns None (skip setting it) if "Description" exists as some other
    property type - never overwrite an unrelated existing column."""
    if "Description" in properties:
        return "Description" if properties["Description"].get("type") == "rich_text" else None

    await client.data_sources.update(data_source_id, properties={"Description": {"rich_text": {}}})
    return "Description"


def _text_block(block_type: str, content: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": [{"type": "text", "text": {"content": content}}]},
    }


def _render_detail_text(task: GeneratedTask) -> str:
    """Plain-text rendering of the whole task detail — description, key
    points, location, link — in the same order the app's task modal shows
    them. Used for the "Description" grid property so the column carries
    everything, not just the first sentence (the page body still gets the
    richer block version via _build_children)."""
    parts: list[str] = []
    if task.details.description:
        parts.append(task.details.description)
    if task.details.key_points:
        parts.append("\n".join(f"• {point}" for point in task.details.key_points))
    if task.details.location:
        parts.append(f"Location: {task.details.location}")
    if task.details.link:
        parts.append(f"Link: {task.details.link}")
    return "\n\n".join(parts)


def _build_children(task: GeneratedTask) -> list[dict]:
    children: list[dict] = []
    if task.details.description:
        children.append(_text_block("paragraph", task.details.description))
    children.extend(
        _text_block("bulleted_list_item", point) for point in task.details.key_points
    )
    if task.details.location:
        children.append(_text_block("paragraph", f"Location: {task.details.location}"))
    if task.details.link:
        children.append(_text_block("paragraph", f"Link: {task.details.link}"))
    if not children:
        children.append(_text_block("paragraph", "(no details)"))
    return children


async def _replace_children(client: AsyncClient, page_id: str, children: list[dict]) -> None:
    """Swaps a page's body blocks for `children` - Notion has no
    "replace children" call, only list/delete/append, so an update clears
    the old blocks first rather than appending on top of them (which would
    just accumulate duplicate content on every re-push)."""
    existing = await client.blocks.children.list(block_id=page_id)
    for block in existing.get("results", []):
        await client.blocks.delete(block_id=block["id"])
    if children:
        await client.blocks.children.append(block_id=page_id, children=children)


async def push_to_notion(
    task: GeneratedTask, integration: Integration, existing_page_id: str | None = None
) -> tuple[str, str]:
    """Creates a page in the user's configured Notion database for `task`,
    or - when `existing_page_id` is given (a prior successful push for this
    task, per `push_task`'s PushLog lookup) - updates that page in place
    instead of creating a second one. Returns (url, page_id); the id is
    what a later re-push needs to update this same page again.

    Raises NotionPushError on any failure — caller (push_task) is the one
    that logs it to `push_logs`."""
    secret = await CredentialService.get(task.user_id, "notion")
    if secret is None:
        raise NotionPushError("Notion is not connected")

    data_source_id = integration.target_config.get("data_source_id")
    if not data_source_id:
        raise NotionPushError("Notion integration is missing its data source")

    client = AsyncClient(auth=secret["token"])
    try:
        # Property *names* are user-defined per database (only the title
        # property is guaranteed to exist) — look the schema up per push
        # rather than hardcoding "Name", which would silently mismatch any
        # database that titled its title column something else.
        data_source = await client.data_sources.retrieve(data_source_id)
        properties_schema = data_source.get("properties", {})
        title_property = _find_property(properties_schema, "title")
        if title_property is None:
            raise NotionPushError("Target database has no title property")

        properties: dict = {
            title_property: {"title": [{"type": "text", "text": {"content": task.title}}]}
        }
        if task.due_date is not None:
            date_property = _find_property(properties_schema, "date")
            if date_property is not None:
                properties[date_property] = {
                    "date": {"start": task.due_date.date().isoformat()}
                }

        status_property = _named_select_property(properties_schema, "Status")
        if status_property is not None:
            properties[status_property] = {
                "select": {"name": STATUS_LABELS.get(task.status, task.status)}
            }

        task_type_property = _named_select_property(properties_schema, "Task Type")
        if task_type_property is not None:
            properties[task_type_property] = {
                "select": {"name": TASK_TYPE_LABELS.get(task.task_type, task.task_type)}
            }

        detail_text = _render_detail_text(task)
        if detail_text:
            description_property = await _ensure_description_property(
                client, data_source_id, properties_schema
            )
            if description_property is not None:
                properties[description_property] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": detail_text[:DESCRIPTION_PROPERTY_MAX_LEN]},
                        }
                    ]
                }

        if existing_page_id is not None:
            page = await client.pages.update(page_id=existing_page_id, properties=properties)
            await _replace_children(client, existing_page_id, _build_children(task))
        else:
            page = await client.pages.create(
                parent={"type": "data_source_id", "data_source_id": data_source_id},
                properties=properties,
                children=_build_children(task),
            )
    except NotionPushError:
        raise
    except Exception as exc:
        raise NotionPushError(str(exc)) from exc
    finally:
        await client.aclose()

    url = page.get("url")
    page_id = page.get("id")
    if not url or not page_id:
        raise NotionPushError("Notion did not return a page URL/id")
    return url, page_id

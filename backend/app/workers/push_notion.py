from notion_client import AsyncClient

from app.models.generated_task import GeneratedTask
from app.models.integration import Integration
from app.services.credentials import CredentialService


class NotionPushError(Exception):
    pass


def _find_property(properties: dict, prop_type: str) -> str | None:
    for name, schema in properties.items():
        if schema.get("type") == prop_type:
            return name
    return None


def _text_block(block_type: str, content: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": [{"type": "text", "text": {"content": content}}]},
    }


def _build_children(task: GeneratedTask) -> list[dict]:
    lines = []
    if task.details.description:
        lines.append(task.details.description)
    if task.details.location:
        lines.append(f"Location: {task.details.location}")
    if task.details.link:
        lines.append(f"Link: {task.details.link}")
    if not lines:
        lines.append("(no details)")

    children = [_text_block("paragraph", line) for line in lines]
    children.extend(_text_block("bulleted_list_item", point) for point in task.details.key_points)
    return children


async def push_to_notion(task: GeneratedTask, integration: Integration) -> str:
    """Creates a page in the user's configured Notion database for `task`.
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
    if not url:
        raise NotionPushError("Notion did not return a page URL")
    return url

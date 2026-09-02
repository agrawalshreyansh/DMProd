from notion_client import APIResponseError, AsyncClient
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.integration import Integration
from app.models.user import User
from app.services.credentials import CredentialService

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


class NotionConnectRequest(BaseModel):
    token: str
    database_id: str


class NotionStatus(BaseModel):
    connected: bool
    database_id: str | None = None
    database_title: str | None = None


def _database_title(database: dict) -> str | None:
    text = "".join(part.get("plain_text", "") for part in database.get("title") or [])
    return text or None


@router.post("/notion", response_model=NotionStatus)
async def connect_notion(
    body: NotionConnectRequest, user: User = Depends(get_current_user)
) -> NotionStatus:
    client = AsyncClient(auth=body.token)
    try:
        database = await client.databases.retrieve(body.database_id)
    except APIResponseError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Could not access that database — check the token and that the "
            f"database is shared with the integration ({exc}).",
        )
    finally:
        await client.aclose()

    data_sources = database.get("data_sources") or []
    if not data_sources:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That database has no accessible data source."
        )

    await CredentialService.set(str(user.id), "notion", {"token": body.token})

    target_config = {
        "database_id": body.database_id,
        "data_source_id": data_sources[0]["id"],
        "database_title": _database_title(database),
    }
    existing = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "notion"
    )
    if existing:
        existing.target_config = target_config
        existing.enabled = True
        await existing.save()
    else:
        await Integration(
            user_id=str(user.id), type="notion", target_config=target_config
        ).insert()

    return NotionStatus(
        connected=True,
        database_id=target_config["database_id"],
        database_title=target_config["database_title"],
    )


@router.get("/notion", response_model=NotionStatus)
async def get_notion_status(user: User = Depends(get_current_user)) -> NotionStatus:
    integration = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "notion"
    )
    if integration is None or not integration.enabled:
        return NotionStatus(connected=False)
    return NotionStatus(
        connected=True,
        database_id=integration.target_config.get("database_id"),
        database_title=integration.target_config.get("database_title"),
    )


@router.delete("/notion", response_model=NotionStatus)
async def disconnect_notion(user: User = Depends(get_current_user)) -> NotionStatus:
    await CredentialService.delete(str(user.id), "notion")
    integration = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "notion"
    )
    if integration is not None:
        await integration.delete()
    return NotionStatus(connected=False)

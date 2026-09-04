import httpx
from notion_client import APIResponseError, AsyncClient
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.integration import Integration
from app.models.user import User
from app.services.credentials import CredentialService
from app.services.google_oauth import (
    GoogleOAuthError,
    build_authorize_url,
    exchange_code,
    is_configured,
)
from app.workers.push_notion import STATUS_LABELS, TASK_TYPE_LABELS

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


async def _ensure_task_schema(client: AsyncClient, data_source_id: str) -> None:
    """Adds Due Date/Status/Task Type columns if the database doesn't
    already have them, so a fresh (just-created) database gets somewhere
    for push_to_notion to put those fields instead of everything landing
    in the page body. Never touches/removes existing properties — Notion's
    update-a-data-source PATCH only creates or edits the keys you send."""
    data_source = await client.data_sources.retrieve(data_source_id)
    properties = data_source.get("properties", {})
    to_add: dict = {}

    if not any(p.get("type") == "date" for p in properties.values()):
        to_add["Due Date"] = {"date": {}}
    if "Status" not in properties:
        to_add["Status"] = {"select": {"options": [{"name": v} for v in STATUS_LABELS.values()]}}
    if "Task Type" not in properties:
        to_add["Task Type"] = {
            "select": {"options": [{"name": v} for v in TASK_TYPE_LABELS.values()]}
        }

    if to_add:
        await client.data_sources.update(data_source_id, properties=to_add)


@router.post("/notion", response_model=NotionStatus)
async def connect_notion(
    body: NotionConnectRequest, user: User = Depends(get_current_user)
) -> NotionStatus:
    client = AsyncClient(auth=body.token)
    try:
        try:
            database = await client.databases.retrieve(body.database_id)
        except APIResponseError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Could not access that database — check the token and that the "
                f"database is shared with the integration ({exc}).",
            )

        data_sources = database.get("data_sources") or []
        if not data_sources:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "That database has no accessible data source."
            )
        data_source_id = data_sources[0]["id"]

        try:
            await _ensure_task_schema(client, data_source_id)
        except APIResponseError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Connected, but couldn't set up the Status/Due Date/Task Type "
                f"columns automatically ({exc}). Make sure the integration has "
                f"write access, or add those columns yourself.",
            )
    finally:
        await client.aclose()

    await CredentialService.set(str(user.id), "notion", {"token": body.token})

    target_config = {
        "database_id": body.database_id,
        "data_source_id": data_source_id,
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


class GoogleAuthorizeUrl(BaseModel):
    authorize_url: str


class GoogleCallbackRequest(BaseModel):
    code: str


class GoogleCalendarStatus(BaseModel):
    connected: bool
    calendar_summary: str | None = None


async def _fetch_primary_calendar_summary(access_token: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    # Cosmetic lookup only — a failure here shouldn't fail the connection
    # itself, the calendar_id ("primary") still works without a display name.
    return resp.json().get("summary") if resp.status_code == 200 else None


@router.get("/google-calendar/connect", response_model=GoogleAuthorizeUrl)
async def google_calendar_connect(
    state: str, user: User = Depends(get_current_user)
) -> GoogleAuthorizeUrl:
    if not is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Google Calendar isn't configured on this server.",
        )
    return GoogleAuthorizeUrl(authorize_url=build_authorize_url(state))


@router.post("/google-calendar/callback", response_model=GoogleCalendarStatus)
async def google_calendar_callback(
    body: GoogleCallbackRequest, user: User = Depends(get_current_user)
) -> GoogleCalendarStatus:
    try:
        tokens = await exchange_code(body.code)
    except GoogleOAuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    await CredentialService.set(str(user.id), "google", tokens)
    calendar_summary = await _fetch_primary_calendar_summary(tokens["access_token"])

    target_config = {"calendar_id": "primary", "calendar_summary": calendar_summary}
    existing = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "google_calendar"
    )
    if existing:
        existing.target_config = target_config
        existing.enabled = True
        await existing.save()
    else:
        await Integration(
            user_id=str(user.id), type="google_calendar", target_config=target_config
        ).insert()

    return GoogleCalendarStatus(connected=True, calendar_summary=calendar_summary)


@router.get("/google-calendar", response_model=GoogleCalendarStatus)
async def get_google_calendar_status(
    user: User = Depends(get_current_user),
) -> GoogleCalendarStatus:
    integration = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "google_calendar"
    )
    if integration is None or not integration.enabled:
        return GoogleCalendarStatus(connected=False)
    return GoogleCalendarStatus(
        connected=True, calendar_summary=integration.target_config.get("calendar_summary")
    )


@router.delete("/google-calendar", response_model=GoogleCalendarStatus)
async def disconnect_google_calendar(
    user: User = Depends(get_current_user),
) -> GoogleCalendarStatus:
    # One shared "google" credential today has exactly one consumer
    # (Calendar) — disconnecting takes it down too. When Sheets reuses this
    # same credential, this delete needs to also clear its Integration doc,
    # since revoking here invalidates the token for both.
    await CredentialService.delete(str(user.id), "google")
    integration = await Integration.find_one(
        Integration.user_id == str(user.id), Integration.type == "google_calendar"
    )
    if integration is not None:
        await integration.delete()
    return GoogleCalendarStatus(connected=False)

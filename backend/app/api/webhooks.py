import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.config import settings
from app.models.webhook_event_log import WebhookEventLog
from app.services.webhook_security import verify_signature

logger = logging.getLogger("webhooks.instagram")

router = APIRouter(prefix="/webhooks/instagram", tags=["webhooks"])


@router.get("")
async def verify_subscription(request: Request) -> Response:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and challenge and token == settings.webhook_verify_token:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status.HTTP_403_FORBIDDEN, "Verification failed")


def _log_messaging_event(event: dict[str, Any]) -> None:
    # ponytail: field extraction is deliberately tolerant/best-effort — the
    # exact attachment shape for a shared reel isn't confirmed against a
    # real payload yet (that's what the manual DM test in this phase is
    # for). Log everything available rather than assume a schema.
    sender_id = event.get("sender", {}).get("id")
    message = event.get("message", {})
    attachments = message.get("attachments", [])
    attachment_types = [a.get("type") for a in attachments]

    logger.info(
        "instagram webhook event sender_id=%s message_id=%s attachment_types=%s timestamp=%s",
        sender_id,
        message.get("mid"),
        attachment_types,
        event.get("timestamp"),
    )


@router.post("")
async def receive_event(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    raw_body = await request.body()

    if not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    payload = await request.json()
    await WebhookEventLog(raw_payload=payload).insert()

    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            _log_messaging_event(event)

    return Response(status_code=status.HTTP_200_OK)

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.config import settings
from app.models.instagram_account import InstagramAccount
from app.models.pending_verification import PendingVerification
from app.models.reel import Reel
from app.models.webhook_event_log import WebhookEventLog
from app.services.instagram_profile import fetch_username
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


async def _store_reel_if_any(user_id: str, sender_ig_id: str, event: dict[str, Any]) -> None:
    message = event.get("message", {})
    message_id = message.get("mid")
    if not message_id:
        return

    for attachment in message.get("attachments", []):
        if attachment.get("type") != "ig_reel":
            continue
        # Meta can redeliver the same webhook event — check first so a
        # redelivery is a no-op instead of a raised DuplicateKeyError.
        if await Reel.find_one(Reel.message_id == message_id):
            return
        payload = attachment.get("payload", {})
        await Reel(
            user_id=user_id,
            sender_ig_id=sender_ig_id,
            message_id=message_id,
            reel_video_id=payload.get("reel_video_id"),
            url=payload.get("url"),
            caption=payload.get("title"),
        ).insert()


async def _try_verify_code(sender_id: str, event: dict[str, Any]) -> bool:
    # ponytail: `message.text` is the Messenger-derived field name for a
    # plain-text DM body — not yet confirmed against a real Instagram DM the
    # way the reel-attachment shape was; the manual test for this feature is
    # what confirms it.
    text = event.get("message", {}).get("text")
    if not text:
        return False

    pending = await PendingVerification.find_one(PendingVerification.code == text.strip().upper())
    if pending is None:
        return False

    # Motor/mongomock hand back naive datetimes on read even though we write
    # tz-aware ones — normalize before comparing.
    expires_at = pending.expires_at.replace(tzinfo=pending.expires_at.tzinfo or timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await pending.delete()
        return False

    if await InstagramAccount.find_one(InstagramAccount.ig_user_id == sender_id):
        return False

    try:
        username = await fetch_username(sender_id) or ""
    except Exception:
        # Cosmetic lookup — the link itself must not depend on it succeeding.
        username = ""
        logger.exception("failed to fetch instagram username for sender_id=%s", sender_id)

    await InstagramAccount(user_id=pending.user_id, ig_user_id=sender_id, username=username).insert()
    await pending.delete()
    logger.info(
        "verified instagram account sender_id=%s user_id=%s username=%s via DM code",
        sender_id,
        pending.user_id,
        username,
    )
    return True


async def _handle_messaging_event(event: dict[str, Any]) -> None:
    # ponytail: field extraction is deliberately tolerant/best-effort — log
    # everything available rather than assume a schema, in case Meta sends
    # message types we haven't seen yet.
    sender_id = event.get("sender", {}).get("id")
    message = event.get("message", {})
    attachments = message.get("attachments", [])
    attachment_types = [a.get("type") for a in attachments]

    account = await InstagramAccount.find_one(InstagramAccount.ig_user_id == sender_id) if sender_id else None

    logger.info(
        "instagram webhook event sender_id=%s user_id=%s message_id=%s attachment_types=%s timestamp=%s",
        sender_id,
        account.user_id if account else None,
        message.get("mid"),
        attachment_types,
        event.get("timestamp"),
    )

    if account is None:
        if sender_id and await _try_verify_code(sender_id, event):
            return
        logger.info("unlinked sender_id=%s, ignoring", sender_id)
        return

    await _store_reel_if_any(account.user_id, sender_id, event)


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
            await _handle_messaging_event(event)

    return Response(status_code=status.HTTP_200_OK)

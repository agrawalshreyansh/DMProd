import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from app.models.comment_unlock_request import CommentUnlockRequest
from app.models.generated_task import GeneratedTask
from app.models.reel import Reel
from app.queue import get_queue
from app.services.instagram_private import InstagramPrivateError, comment_on_reel, follow_user
from app.workers.push import push_task

logger = logging.getLogger("worker.comment_unlock")

# A creator (or their automation) that hasn't replied by then almost
# certainly isn't going to — stop waiting rather than hold the request
# open, and unrelated, forever.
EXPIRY = timedelta(hours=72)

_URL_RE = re.compile(r"https?://\S+")


def _safe_url(url: str | None) -> str | None:
    """None unless `url` is http(s) — a template button's URL comes from
    an untrusted DM payload (anyone who DMs the bot controls it, not just
    the reel's actual creator, per the FIFO best-effort matching this
    phase already accepts), so a `javascript:`/`data:` scheme must never
    reach `details.link` and get rendered as a link later."""
    if not url:
        return None
    return url if urlparse(url).scheme in ("http", "https") else None


async def trigger_comment_unlock(reel: Reel, keyword: str) -> None:
    """Follows the reel's creator and comments `keyword` on it — once per
    reel (idempotency: does a CommentUnlockRequest already exist for this
    reel_id?), not per user, since a Reel is shared content. Never raises:
    a failure here means the bonus enrichment doesn't happen, not that the
    per-user task generation that already succeeded should be undone."""
    reel_id = str(reel.id)
    if await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == reel_id):
        return

    if not reel.creator_username or not reel.url:
        logger.warning(
            "comment_unlock: reel_id=%s missing creator_username/url, skipping", reel_id
        )
        reel.comment_unlock_status = "failed"
        await reel.save()
        return

    try:
        await follow_user(reel.creator_username)
        await comment_on_reel(reel.url, keyword)
    except InstagramPrivateError as exc:
        # ponytail: no unfollow-cleanup here — unfollow is deliberately not
        # automated at all (see the phase's Risks note), so a partial
        # failure (followed but didn't comment) just leaves the bot
        # following. Accepted trade-off for fewer automated API calls.
        logger.warning("comment_unlock failed reel_id=%s error=%s", reel_id, exc)
        reel.comment_unlock_status = "failed"
        await reel.save()
        return

    # Only recorded once both actions succeed — a CommentUnlockRequest
    # existing is exactly what the idempotency check above relies on, so a
    # partial failure (followed but didn't comment) intentionally leaves no
    # request behind, letting the next share of this reel retry cleanly.
    await CommentUnlockRequest(
        reel_id=reel_id,
        creator_username=reel.creator_username,
        keyword=keyword,
        followed_at=datetime.now(timezone.utc),
    ).insert()

    reel.comment_unlock_status = "pending"
    reel.comment_unlock_keyword = keyword
    await reel.save()
    logger.info(
        "comment_unlock: commented %r on reel_id=%s (creator=@%s)",
        keyword,
        reel_id,
        reel.creator_username,
    )


async def _expire(request: CommentUnlockRequest) -> None:
    request.status = "expired"
    await request.save()

    reel = await Reel.get(request.reel_id)
    if reel is not None:
        reel.comment_unlock_status = "expired"
        await reel.save()


async def _oldest_pending(now: datetime) -> CommentUnlockRequest | None:
    """The oldest still-pending request, expiring any that have aged out
    along the way — the "lazy check-on-read" expiry the plan calls for, no
    separate scheduled sweep needed."""
    candidates = (
        await CommentUnlockRequest.find(CommentUnlockRequest.status == "pending")
        .sort(+CommentUnlockRequest.commented_at)
        .to_list()
    )
    for candidate in candidates:
        commented_at = candidate.commented_at.replace(
            tzinfo=candidate.commented_at.tzinfo or timezone.utc
        )
        if now - commented_at > EXPIRY:
            await _expire(candidate)
            continue
        return candidate
    return None


def _first_url(obj: object) -> str | None:
    """First http(s) URL found anywhere in a nested dict/list/string. DM-
    automation tools and IG itself bury the real link at inconsistent
    depths (button URL, `payload.url`, a redirect wrapper, plain text in a
    card title), so a structural walk beats hardcoding every nest."""
    if isinstance(obj, str):
        match = _URL_RE.search(obj)
        return _safe_url(match.group(0)) if match else None
    if isinstance(obj, dict):
        for value in obj.values():
            found = _first_url(value)
            if found:
                return found
    if isinstance(obj, list):
        for value in obj:
            found = _first_url(value)
            if found:
                return found
    return None


def _extract_reply_content(message: dict) -> tuple[str, str | None] | None:
    """(display_text, explicit_link) from a DM's message payload, or None
    when it carries no usable text or URL at all.

    Shapes seen in the wild:
    - plain `message.text`
    - a Messenger-style "generic template" card: `payload.generic.
      elements[0]` with a `title` and a `buttons[].url` (confirmed against
      SuperProfile.bio; likely the common shape since most creators run
      "comment X for DM" through automation, not a hand-typed reply)
    - a "button template": `buttons` at the payload root
    - `payload.url` directly on an attachment
    - a URL buried deeper in the payload (redirect wrappers etc.)

    The button URL is taken structurally, never regexed out of the title
    (the title only shows the button's *label*, e.g. "Explore Now!")."""
    text = (message.get("text") or "").strip()
    attachments = message.get("attachments") or []

    explicit_link: str | None = None
    title_text = ""
    for attachment in attachments:
        payload = attachment.get("payload") or {}
        elements = payload.get("generic", {}).get("elements", []) if isinstance(payload, dict) else []
        if elements:
            element = elements[0]
            title_text = title_text or element.get("title", "")
            for button in element.get("buttons", []) or []:
                explicit_link = explicit_link or _safe_url(button.get("url"))
        if isinstance(payload, dict):
            for button in payload.get("buttons", []) or []:
                explicit_link = explicit_link or _safe_url(button.get("url"))
            explicit_link = explicit_link or _safe_url(payload.get("url"))

    quick_reply = message.get("quick_reply") or {}
    explicit_link = explicit_link or _safe_url(quick_reply.get("payload"))

    display_text = text or title_text
    link = explicit_link or _first_url(attachments)

    if not display_text and not link:
        return None
    return display_text, link


async def fulfill_comment_unlock(request: CommentUnlockRequest, message: dict) -> None:
    """Merges the DM's content into every GeneratedTask tied to the
    request's reel (reel-level, not per-user — mirrors how task generation
    itself fans out per user for a shared Reel), re-pushes each, and marks
    the request fulfilled. Doesn't unfollow — that's deliberately not
    automated (see the phase's Risks note), the bot just stays following."""
    content = _extract_reply_content(message)
    reply_text, explicit_link = content if content else ("", None)
    url_match = _URL_RE.search(reply_text)
    link = explicit_link or (_safe_url(url_match.group(0)) if url_match else None)
    message_id = message.get("mid")

    tasks = await GeneratedTask.find(GeneratedTask.reel_id == request.reel_id).to_list()
    for task in tasks:
        lines = [task.details.description] if task.details.description else []
        lines.append(f"Creator's reply: {reply_text}")
        task.details.description = "\n\n".join(lines)
        if link and not task.details.link:
            task.details.link = link
        await task.save()
        get_queue().enqueue(push_task, str(task.id))

    request.status = "fulfilled"
    request.reply_text = reply_text
    request.reply_message_id = message_id
    request.reply_raw = message
    request.fulfilled_at = datetime.now(timezone.utc)
    await request.save()

    reel = await Reel.get(request.reel_id)
    if reel is not None:
        reel.comment_unlock_status = "fulfilled"
        await reel.save()

    logger.info(
        "comment_unlock: fulfilled reel_id=%s from @%s, updated %d task(s)",
        request.reel_id,
        request.creator_username,
        len(tasks),
    )


async def try_fulfill_from_dm(message: dict) -> bool:
    """True if `message` was consumed as a reply to some pending
    CommentUnlockRequest. Matching is FIFO-oldest-pending, not guaranteed-
    correct attribution — see the phase's Risks on why a better match
    isn't possible (the creator's id is never known before they DM).
    False for a message shape we don't understand (out of scope) or when
    nothing is pending — caller falls back to its normal unlinked-sender
    handling either way."""
    message_id = message.get("mid")
    if message_id and await CommentUnlockRequest.find_one(
        CommentUnlockRequest.reply_message_id == message_id
    ):
        return True  # already processed this exact DM — a Meta redelivery

    request = await _oldest_pending(datetime.now(timezone.utc))
    if request is None:
        return False

    if _extract_reply_content(message) is None:
        # A request is pending but this DM carries no text or URL we can
        # use — IG sometimes delivers CTA/button cards as
        # type="unsupported" with no payload. Don't consume the request
        # (a real follow-up reply might still come); log loudly so the raw
        # payload in webhook_event_logs can be recovered by hand.
        logger.warning(
            "comment_unlock: request pending for reel_id=%s but DM mid=%s is unparseable "
            "(attachment_types=%s) — not fulfilled, recover from webhook_event_logs",
            request.reel_id,
            message_id,
            [a.get("type") for a in message.get("attachments") or []],
        )
        return False

    await fulfill_comment_unlock(request, message)
    return True

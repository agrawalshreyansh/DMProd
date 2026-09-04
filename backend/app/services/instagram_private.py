import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from instagrapi import Client

from app.config import settings

logger = logging.getLogger("services.instagram_private")

# Deliberately outside app/ — same tier as .env, holds an equally live,
# reusable login. Gitignored; see backend/.gitignore.
SESSION_FILE = Path(__file__).resolve().parents[2] / ".instagrapi_session.json"

# Single worker: instagrapi's Client isn't safe to hit concurrently from
# multiple threads, and serializing every call onto one thread also means
# actions naturally land one at a time rather than bursting — the plan's
# own "don't look like a bot" rule (see phase-09-comment-to-unlock.md's
# Risks), not just a thread-safety fix.
_executor = ThreadPoolExecutor(max_workers=1)
_client: Client | None = None


class InstagramPrivateError(Exception):
    """instagrapi isn't configured, its session/login failed, or an action
    (follow/comment) failed. Never retried automatically — an invalidated
    session needs a human to re-extract INSTAGRAM_SESSION_ID, per the
    plan's Risks note, not a bug to paper over with a retry loop."""


def _get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    if not settings.instagram_session_id:
        raise InstagramPrivateError("INSTAGRAM_SESSION_ID is not configured")

    client = Client()
    if SESSION_FILE.exists():
        client.load_settings(SESSION_FILE)
    try:
        client.login_by_sessionid(settings.instagram_session_id)
    except Exception as exc:
        raise InstagramPrivateError(f"instagrapi login failed: {exc}") from exc
    client.dump_settings(SESSION_FILE)

    _client = client
    return client


async def _run(fn) -> None:
    await asyncio.get_running_loop().run_in_executor(_executor, fn)


async def follow_user(username: str) -> None:
    def _do() -> None:
        client = _get_client()
        try:
            user_id = client.user_id_from_username(username)
            client.user_follow(user_id)
        except Exception as exc:
            raise InstagramPrivateError(f"failed to follow @{username}: {exc}") from exc

    await _run(_do)
    logger.info("followed @%s via instagrapi", username)


async def comment_on_reel(url: str, text: str) -> None:
    def _do() -> None:
        client = _get_client()
        try:
            media_pk = client.media_pk_from_url(url)
            media_id = client.media_id(media_pk)
            client.media_comment(media_id, text)
        except Exception as exc:
            raise InstagramPrivateError(f"failed to comment on {url}: {exc}") from exc

    await _run(_do)
    logger.info("commented %r on %s via instagrapi", text, url)

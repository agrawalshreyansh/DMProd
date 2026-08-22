import httpx

from app.config import settings

PROFILE_URL = "https://graph.instagram.com/v21.0"


async def fetch_username(ig_user_id: str) -> str | None:
    """Look up the username for someone who's messaged the bot, using the
    bot's own access token — not the user's, they never gave us one."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PROFILE_URL}/{ig_user_id}",
            params={"fields": "username", "access_token": settings.instagram_bot_access_token},
        )
        resp.raise_for_status()
        return resp.json().get("username")

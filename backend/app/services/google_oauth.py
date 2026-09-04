import time
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.services.credentials import CredentialService

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# calendar.events (not the broader "calendar" scope) — create/edit events
# only, no access to calendar settings/sharing. calendar.freebusy is the
# narrowest scope that covers the freeBusy.query call used to avoid
# double-booking (confirmed against Google's OAuth scope reference — it's
# purpose-built for exactly this, doesn't expose event details). Shared
# across every Google integration that reuses this OAuth app (Sheets,
# later) by adding its own scope to this list, not a second OAuth flow.
#
# Changing this list changes what's granted on the NEXT consent — anyone
# already connected under the old scope set needs to disconnect/reconnect
# for calendar.freebusy to actually be on their token.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]


class GoogleOAuthError(Exception):
    """Not connected, or Google rejected a token exchange/refresh."""


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def redirect_uri() -> str:
    return f"{settings.cors_origin}/api/google-calendar/callback"


def build_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # offline+consent: without both, Google only issues a refresh_token
        # on a user's very first authorization — a reconnect after revoking
        # access would otherwise silently come back with no refresh_token.
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise GoogleOAuthError(f"Google rejected the authorization code: {resp.text}")

    body = resp.json()
    if "refresh_token" not in body:
        raise GoogleOAuthError(
            "Google did not return a refresh token — try disconnecting any prior "
            "grant for this app in your Google Account permissions, then reconnect."
        )
    return {
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "expires_at": time.time() + body["expires_in"],
    }


async def _refresh(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise GoogleOAuthError(f"Google Calendar token refresh failed: {resp.text}")

    body = resp.json()
    return {
        "access_token": body["access_token"],
        "refresh_token": refresh_token,  # Google doesn't resend it on refresh
        "expires_at": time.time() + body["expires_in"],
    }


async def get_valid_access_token(user_id: str) -> str | None:
    """A usable access token for `user_id`'s Google credential, refreshing
    it first if it's expired (or about to be). None if never connected."""
    secret = await CredentialService.get(user_id, "google")
    if secret is None:
        return None

    if time.time() < secret["expires_at"] - 60:
        return secret["access_token"]

    refreshed = await _refresh(secret["refresh_token"])
    await CredentialService.set(user_id, "google", refreshed)
    return refreshed["access_token"]

import json
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.models.user_credential import Provider, UserCredential

_fernet = Fernet(settings.app_encryption_key.encode())


class CredentialService:
    """Only code path allowed to read/write `user_credentials`.

    Secrets are stored as an opaque Fernet-encrypted JSON blob; callers pass
    a plain dict shaped however that provider needs (e.g. {"api_key": "..."}
    for Gemini, {"access_token": "...", "refresh_token": "..."} for OAuth
    providers added in later phases).
    """

    @staticmethod
    async def set(user_id: str, provider: Provider, secret: dict[str, Any]) -> UserCredential:
        encrypted = _fernet.encrypt(json.dumps(secret).encode()).decode()
        existing = await UserCredential.find_one(
            UserCredential.user_id == user_id, UserCredential.provider == provider
        )
        if existing:
            existing.encrypted_secret = encrypted
            existing.updated_at = datetime.now(timezone.utc)
            await existing.save()
            return existing

        credential = UserCredential(
            user_id=user_id, provider=provider, encrypted_secret=encrypted
        )
        await credential.insert()
        return credential

    @staticmethod
    async def get(user_id: str, provider: Provider) -> dict[str, Any] | None:
        credential = await UserCredential.find_one(
            UserCredential.user_id == user_id, UserCredential.provider == provider
        )
        if credential is None:
            return None
        try:
            return json.loads(_fernet.decrypt(credential.encrypted_secret.encode()))
        except InvalidToken:
            return None

    @staticmethod
    async def delete(user_id: str, provider: Provider) -> bool:
        credential = await UserCredential.find_one(
            UserCredential.user_id == user_id, UserCredential.provider == provider
        )
        if credential is None:
            return False
        await credential.delete()
        return True

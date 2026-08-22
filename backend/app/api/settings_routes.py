from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.credentials import CredentialService

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class GeminiKeyRequest(BaseModel):
    api_key: str


class GeminiKeyStatus(BaseModel):
    connected: bool
    masked_key: str | None = None


def _mask(api_key: str) -> str:
    if len(api_key) <= 4:
        return "•" * len(api_key)
    return "••••" + api_key[-4:]


@router.put("/gemini-key", response_model=GeminiKeyStatus)
async def set_gemini_key(
    body: GeminiKeyRequest, user: User = Depends(get_current_user)
) -> GeminiKeyStatus:
    # CredentialService.set upserts on the (user_id, provider) unique index,
    # so this always replaces the previous key — only one can ever be active.
    await CredentialService.set(str(user.id), "gemini", {"api_key": body.api_key})
    return GeminiKeyStatus(connected=True, masked_key=_mask(body.api_key))


@router.get("/gemini-key", response_model=GeminiKeyStatus)
async def get_gemini_key_status(user: User = Depends(get_current_user)) -> GeminiKeyStatus:
    secret = await CredentialService.get(str(user.id), "gemini")
    if secret is None:
        return GeminiKeyStatus(connected=False)
    return GeminiKeyStatus(connected=True, masked_key=_mask(secret["api_key"]))

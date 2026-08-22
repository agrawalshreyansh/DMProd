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


@router.put("/gemini-key", response_model=GeminiKeyStatus)
async def set_gemini_key(
    body: GeminiKeyRequest, user: User = Depends(get_current_user)
) -> GeminiKeyStatus:
    await CredentialService.set(str(user.id), "gemini", {"api_key": body.api_key})
    return GeminiKeyStatus(connected=True)


@router.get("/gemini-key", response_model=GeminiKeyStatus)
async def get_gemini_key_status(user: User = Depends(get_current_user)) -> GeminiKeyStatus:
    secret = await CredentialService.get(str(user.id), "gemini")
    return GeminiKeyStatus(connected=secret is not None)

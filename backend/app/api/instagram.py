import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.instagram_account import InstagramAccount
from app.models.pending_verification import PendingVerification
from app.models.user import User

router = APIRouter(prefix="/api/v1/instagram", tags=["instagram"])

# 0/O/1/I dropped — easy to misread when copying a code into a DM by hand.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
CODE_LENGTH = 6
CODE_TTL_MINUTES = 15


def _generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


async def _unique_code() -> str:
    for _ in range(10):
        code = _generate_code()
        if await PendingVerification.find_one(PendingVerification.code == code) is None:
            return code
    raise RuntimeError("could not generate a unique verification code")


class ConnectResponse(BaseModel):
    code: str
    expires_at: str


class StatusResponse(BaseModel):
    connected: bool
    username: str | None = None


@router.post("/connect", response_model=ConnectResponse)
async def connect(user: User = Depends(get_current_user)) -> ConnectResponse:
    user_id = str(user.id)
    code = await _unique_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)

    existing = await PendingVerification.find_one(PendingVerification.user_id == user_id)
    if existing:
        existing.code = code
        existing.expires_at = expires_at
        await existing.save()
    else:
        await PendingVerification(user_id=user_id, code=code, expires_at=expires_at).insert()

    return ConnectResponse(code=code, expires_at=expires_at.isoformat())


@router.get("/status", response_model=StatusResponse)
async def get_status(user: User = Depends(get_current_user)) -> StatusResponse:
    account = await InstagramAccount.find_one(InstagramAccount.user_id == str(user.id))
    if account is None:
        return StatusResponse(connected=False)
    return StatusResponse(connected=True, username=account.username)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(user: User = Depends(get_current_user)) -> None:
    account = await InstagramAccount.find_one(InstagramAccount.user_id == str(user.id))
    if account:
        await account.delete()

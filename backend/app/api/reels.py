from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.reel import Reel
from app.models.user import User
from app.models.user_reel import UserReel

router = APIRouter(prefix="/api/v1/reels", tags=["reels"])


class ReelOut(BaseModel):
    id: str
    url: str | None
    caption: str | None
    received_at: str


@router.get("", response_model=list[ReelOut])
async def list_reels(user: User = Depends(get_current_user)) -> list[ReelOut]:
    shares = await UserReel.find(UserReel.user_id == str(user.id)).sort(-UserReel.received_at).to_list()
    out = []
    for share in shares:
        reel = await Reel.get(share.reel_id)
        out.append(
            ReelOut(
                id=str(share.id),
                url=reel.url if reel else None,
                caption=reel.caption if reel else None,
                received_at=share.received_at.isoformat(),
            )
        )
    return out

from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.reel import Reel
from app.models.user import User

router = APIRouter(prefix="/api/v1/reels", tags=["reels"])


class ReelOut(BaseModel):
    id: str
    url: str | None
    caption: str | None
    received_at: str


@router.get("", response_model=list[ReelOut])
async def list_reels(user: User = Depends(get_current_user)) -> list[ReelOut]:
    reels = await Reel.find(Reel.user_id == str(user.id)).sort(-Reel.received_at).to_list()
    return [
        ReelOut(id=str(r.id), url=r.url, caption=r.caption, received_at=r.received_at.isoformat())
        for r in reels
    ]

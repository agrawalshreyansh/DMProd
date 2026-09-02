from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.generated_task import TaskType
from app.models.preference import Preference, RoutingTarget
from app.models.user import User

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])

VALID_TASK_TYPES: set[str] = set(TaskType.__args__)
VALID_ROUTING_TARGETS: set[str] = set(RoutingTarget.__args__)


class RoutingBody(BaseModel):
    task_type_routing: dict[str, str | None]


async def _get_or_create(user_id: str) -> Preference:
    preference = await Preference.find_one(Preference.user_id == user_id)
    if preference is None:
        preference = Preference(user_id=user_id)
        await preference.insert()
    return preference


@router.get("", response_model=RoutingBody)
async def get_routing(user: User = Depends(get_current_user)) -> RoutingBody:
    preference = await _get_or_create(str(user.id))
    return RoutingBody(task_type_routing=preference.task_type_routing)


@router.put("", response_model=RoutingBody)
async def set_routing(
    body: RoutingBody, user: User = Depends(get_current_user)
) -> RoutingBody:
    for task_type, target in body.task_type_routing.items():
        if task_type not in VALID_TASK_TYPES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown task_type: {task_type}"
            )
        if target is not None and target not in VALID_ROUTING_TARGETS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown integration: {target}"
            )

    preference = await _get_or_create(str(user.id))
    preference.task_type_routing = body.task_type_routing
    await preference.save()
    return RoutingBody(task_type_routing=preference.task_type_routing)

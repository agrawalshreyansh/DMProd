from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.generated_task import GeneratedTask, TaskDetails, TaskStatus, TaskType
from app.models.reel import Reel
from app.models.user import User

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskOut(BaseModel):
    id: str
    task_type: TaskType
    title: str
    details: TaskDetails
    due_date: str | None
    status: TaskStatus
    reel_url: str | None
    reel_caption: str | None
    created_at: str


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


async def _to_task_out(task: GeneratedTask) -> TaskOut:
    reel = await Reel.get(task.reel_id) if task.reel_id else None
    return TaskOut(
        id=str(task.id),
        task_type=task.task_type,
        title=task.title,
        details=task.details,
        due_date=task.due_date.isoformat() if task.due_date else None,
        status=task.status,
        reel_url=reel.url if reel else None,
        reel_caption=reel.caption if reel else None,
        created_at=task.created_at.isoformat(),
    )


@router.get("", response_model=list[TaskOut])
async def list_tasks(user: User = Depends(get_current_user)) -> list[TaskOut]:
    tasks = (
        await GeneratedTask.find(GeneratedTask.user_id == str(user.id))
        .sort(-GeneratedTask.created_at)
        .to_list()
    )
    return [await _to_task_out(task) for task in tasks]


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task_status(
    task_id: str, body: TaskStatusUpdate, user: User = Depends(get_current_user)
) -> TaskOut:
    task = await GeneratedTask.get(task_id)
    if task is None or task.user_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    task.status = body.status
    await task.save()
    return await _to_task_out(task)

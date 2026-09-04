from datetime import date

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.generated_task import GeneratedTask, TaskDetails, TaskStatus, TaskType
from app.models.push_log import PushLog
from app.models.reel import Reel, VisualEvent
from app.models.user import User
from app.models.user_reel import UserReel

router = APIRouter(prefix="/api/v1/reels", tags=["reels"])


class TaskSummary(BaseModel):
    id: str
    task_type: TaskType
    title: str
    status: TaskStatus


class PushSummary(BaseModel):
    integration_type: str
    external_ref_url: str


class ReelOut(BaseModel):
    id: str
    url: str | None
    caption: str | None
    received_at: str
    reel_status: str
    error_message: str | None
    visual_processing_status: str | None
    task_generation_status: str
    task: TaskSummary | None
    push: PushSummary | None
    # Single field the history page filters/badges on - "failed" (either the
    # content pipeline or this user's task generation failed), a `GeneratedTask`
    # status once one exists, or "processing" while still in between.
    outcome: str


class PushLogOut(BaseModel):
    integration_type: str
    status: str
    external_ref_url: str | None
    error_message: str | None
    pushed_at: str


class ReelDetailOut(BaseModel):
    id: str
    url: str | None
    caption: str | None
    received_at: str
    reel_status: str
    error_message: str | None
    transcript_text: str | None
    transcript_language: str | None
    visual_processing_status: str | None
    visual_summary: str | None
    visual_events: list[VisualEvent]
    comment_unlock_status: str | None
    task_generation_status: str
    task_generation_error: str | None
    task_type: TaskType | None
    title: str | None
    details: TaskDetails | None
    task_status: TaskStatus | None
    push_logs: list[PushLogOut]


def _outcome(reel: Reel | None, user_reel: UserReel, task: GeneratedTask | None) -> str:
    if (reel is not None and reel.status == "failed") or user_reel.task_generation_status == "failed":
        return "failed"
    if task is not None:
        return task.status
    return "processing"


async def _last_push(task: GeneratedTask | None) -> PushLog | None:
    if task is None:
        return None
    return (
        await PushLog.find(PushLog.generated_task_id == str(task.id), PushLog.status == "success")
        .sort(-PushLog.pushed_at)
        .first_or_none()
    )


@router.get("", response_model=list[ReelOut])
async def list_reels(
    user: User = Depends(get_current_user),
    task_type: TaskType | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> list[ReelOut]:
    shares = await UserReel.find(UserReel.user_id == str(user.id)).sort(-UserReel.received_at).to_list()

    out = []
    for share in shares:
        # Plain YYYY-MM-DD (an `<input type="date">` value) - compare dates
        # only, sidestepping naive/aware datetime comparison entirely.
        if date_from and share.received_at.date() < date.fromisoformat(date_from):
            continue
        if date_to and share.received_at.date() > date.fromisoformat(date_to):
            continue

        reel = await Reel.get(share.reel_id)
        task = await GeneratedTask.find_one(
            GeneratedTask.user_id == str(user.id), GeneratedTask.reel_id == share.reel_id
        )
        if task_type is not None and (task is None or task.task_type != task_type):
            continue

        outcome = _outcome(reel, share, task)
        if status_filter is not None and outcome != status_filter:
            continue

        push_log = await _last_push(task)
        out.append(
            ReelOut(
                id=str(share.id),
                url=reel.url if reel else None,
                caption=reel.caption if reel else None,
                received_at=share.received_at.isoformat(),
                reel_status=reel.status if reel else "received",
                error_message=reel.error_message if reel else None,
                visual_processing_status=reel.visual_processing_status if reel else None,
                task_generation_status=share.task_generation_status,
                task=(
                    TaskSummary(
                        id=str(task.id), task_type=task.task_type, title=task.title, status=task.status
                    )
                    if task
                    else None
                ),
                push=(
                    PushSummary(integration_type=push_log.integration_type, external_ref_url=push_log.external_ref_url)
                    if push_log and push_log.external_ref_url
                    else None
                ),
                outcome=outcome,
            )
        )
    return out


@router.get("/{share_id}", response_model=ReelDetailOut)
async def get_reel_detail(share_id: str, user: User = Depends(get_current_user)) -> ReelDetailOut:
    share = await UserReel.get(share_id)
    if share is None or share.user_id != str(user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reel not found")

    reel = await Reel.get(share.reel_id)
    task = await GeneratedTask.find_one(
        GeneratedTask.user_id == str(user.id), GeneratedTask.reel_id == share.reel_id
    )
    push_logs = (
        await PushLog.find(PushLog.generated_task_id == str(task.id)).sort(-PushLog.pushed_at).to_list()
        if task
        else []
    )

    return ReelDetailOut(
        id=str(share.id),
        url=reel.url if reel else None,
        caption=reel.caption if reel else None,
        received_at=share.received_at.isoformat(),
        reel_status=reel.status if reel else "received",
        error_message=reel.error_message if reel else None,
        transcript_text=reel.transcript_text if reel else None,
        transcript_language=reel.transcript_language if reel else None,
        visual_processing_status=reel.visual_processing_status if reel else None,
        visual_summary=reel.visual_summary if reel else None,
        visual_events=reel.visual_events if reel else [],
        comment_unlock_status=reel.comment_unlock_status if reel else None,
        task_generation_status=share.task_generation_status,
        task_generation_error=share.task_generation_error,
        task_type=task.task_type if task else None,
        title=task.title if task else None,
        details=task.details if task else None,
        task_status=task.status if task else None,
        push_logs=[
            PushLogOut(
                integration_type=log.integration_type,
                status=log.status,
                external_ref_url=log.external_ref_url,
                error_message=log.error_message,
                pushed_at=log.pushed_at.isoformat(),
            )
            for log in push_logs
        ],
    )

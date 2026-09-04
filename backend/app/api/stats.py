from datetime import datetime, timedelta, timezone

from beanie.operators import In
from pydantic import BaseModel

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.generated_task import GeneratedTask
from app.models.push_log import PushLog
from app.models.reel import Reel
from app.models.user import User
from app.models.user_reel import UserReel

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class CountBreakdown(BaseModel):
    label: str
    count: int


class StatsOut(BaseModel):
    total_reels: int
    reels_this_week: int
    reels_this_month: int
    reels_succeeded: int
    reels_failed: int
    reels_processing: int
    by_task_type: list[CountBreakdown]
    by_destination: list[CountBreakdown]


@router.get("", response_model=StatsOut)
async def get_stats(user: User = Depends(get_current_user)) -> StatsOut:
    # Plain Python-side counting over this user's own (small, personal-scale)
    # documents rather than a Mongo aggregation pipeline - simpler to get
    # exactly right and to test with exact-match assertions, and correctness
    # doesn't change with volume this low. Revisit with real $group/$count
    # pipelines only if this user's data ever grows enough to make it slow.
    shares = await UserReel.find(UserReel.user_id == str(user.id)).to_list()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    reels_this_week = 0
    reels_this_month = 0
    reels_succeeded = 0
    reels_failed = 0
    reels_processing = 0

    for share in shares:
        received_at = share.received_at.replace(tzinfo=share.received_at.tzinfo or timezone.utc)
        if received_at >= week_ago:
            reels_this_week += 1
        if received_at >= month_ago:
            reels_this_month += 1

        reel = await Reel.get(share.reel_id)
        if (reel is not None and reel.status == "failed") or share.task_generation_status == "failed":
            reels_failed += 1
        elif reel is not None and reel.status == "transcribed":
            reels_succeeded += 1
        else:
            reels_processing += 1

    tasks = await GeneratedTask.find(GeneratedTask.user_id == str(user.id)).to_list()
    task_type_counts: dict[str, int] = {}
    for task in tasks:
        task_type_counts[task.task_type] = task_type_counts.get(task.task_type, 0) + 1

    task_ids = [str(task.id) for task in tasks]
    destination_counts: dict[str, int] = {}
    if task_ids:
        push_logs = await PushLog.find(
            In(PushLog.generated_task_id, task_ids), PushLog.status == "success"
        ).to_list()
        # Distinct tasks per destination, not raw push attempts - a task
        # re-pushed after a comment-unlock DM reply enriches it (Phase 9)
        # leaves multiple successful PushLog rows behind, and "how many
        # tasks went to Notion" shouldn't inflate every time that happens.
        seen: dict[str, set[str]] = {}
        for log in push_logs:
            seen.setdefault(log.integration_type, set()).add(log.generated_task_id)
        destination_counts = {integration: len(task_id_set) for integration, task_id_set in seen.items()}

    return StatsOut(
        total_reels=len(shares),
        reels_this_week=reels_this_week,
        reels_this_month=reels_this_month,
        reels_succeeded=reels_succeeded,
        reels_failed=reels_failed,
        reels_processing=reels_processing,
        by_task_type=[CountBreakdown(label=k, count=v) for k, v in sorted(task_type_counts.items())],
        by_destination=[CountBreakdown(label=k, count=v) for k, v in sorted(destination_counts.items())],
    )

import asyncio
import logging

from app.db import init_db
from app.models.generated_task import GeneratedTask
from app.models.integration import Integration
from app.models.preference import Preference
from app.models.push_log import PushLog
from app.workers.push_gcal import push_to_gcal
from app.workers.push_notion import push_to_notion

logger = logging.getLogger("worker.push")


async def push_task_async(generated_task_id: str) -> None:
    """Routes one GeneratedTask to whichever integration the user's
    Preference maps its task_type to (or does nothing, for null routing)."""
    task = await GeneratedTask.get(generated_task_id)
    if task is None:
        logger.warning("push_task: generated_task_id=%s not found", generated_task_id)
        return

    preference = await Preference.find_one(Preference.user_id == task.user_id)
    target = preference.task_type_routing.get(task.task_type) if preference else None
    if target is None:
        return

    integration = await Integration.find_one(
        Integration.user_id == task.user_id,
        Integration.type == target,
        Integration.enabled == True,  # noqa: E712
    )
    if integration is None:
        await PushLog(
            generated_task_id=str(task.id),
            integration_type=target,
            status="failed",
            error_message=f"{target} is not connected",
        ).insert()
        return

    # A re-push of an already-pushed task (e.g. Phase 9 enriching a task
    # after a comment-unlock DM reply comes back) must update the record it
    # already created, not create a second one with the same title.
    last_push = (
        await PushLog.find(
            PushLog.generated_task_id == str(task.id),
            PushLog.integration_type == target,
            PushLog.status == "success",
        )
        .sort(-PushLog.pushed_at)
        .first_or_none()
    )
    existing_external_id = last_push.external_ref_id if last_push else None

    try:
        if target == "notion":
            external_ref_url, external_ref_id = await push_to_notion(
                task, integration, existing_page_id=existing_external_id
            )
        else:
            external_ref_url, external_ref_id = await push_to_gcal(
                task, integration, existing_event_id=existing_external_id
            )
    except Exception as exc:
        logger.warning(
            "push failed generated_task_id=%s integration=%s error=%s",
            generated_task_id,
            target,
            exc,
        )
        await PushLog(
            generated_task_id=str(task.id),
            integration_type=target,
            status="failed",
            error_message=str(exc),
        ).insert()
        return

    await PushLog(
        generated_task_id=str(task.id),
        integration_type=target,
        status="success",
        external_ref_url=external_ref_url,
        external_ref_id=external_ref_id,
    ).insert()
    logger.info(
        "pushed generated_task_id=%s integration=%s url=%s",
        generated_task_id,
        target,
        external_ref_url,
    )


def push_task(generated_task_id: str) -> None:
    """RQ job entrypoint — same shape as `generate_task`/`process_reel`: a
    plain sync function so each invocation gets its own event loop and
    Motor client."""

    async def _run() -> None:
        await init_db()
        await push_task_async(generated_task_id)

    asyncio.run(_run())

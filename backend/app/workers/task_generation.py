import asyncio
import logging
from datetime import datetime

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.db import init_db
from app.models.generated_task import GeneratedTask, TaskDetails, TaskType
from app.models.reel import Reel
from app.models.user_reel import UserReel
from app.queue import get_queue
from app.services.credentials import CredentialService
from app.workers.comment_unlock import trigger_comment_unlock
from app.workers.push import push_task

logger = logging.getLogger("worker.task_generation")

GEMINI_MODEL = "gemini-3.6-flash"


class TaskGenerationSchema(BaseModel):
    task_type: TaskType
    title: str
    details: TaskDetails
    due_date: str | None = None
    reminder_lead_days: int = 0
    comment_to_unlock_keyword: str | None = None


# Role/rules go in system_instruction (not concatenated into the prompt) so
# the model treats them as standing instructions, separate from the reel's
# own content — the actual per-call input is just caption + transcript.
SYSTEM_INSTRUCTION = """\
You are the task-generation engine for a product where users share Instagram \
reels with a bot and get back a concrete, actionable task — not a summary of \
what the video said. The user shared this specific reel because something in \
it made them want to *do* something: try a recipe, visit a place, buy a \
product, apply a technique, remember an event, save a resource for later. \
Your job is to figure out what that "do" is and hand it back as a task the \
user can act on immediately, without rewatching the reel.

Never write a passive recap of the video's content. If your `title` or \
`details.description` could be mistaken for "what this reel is about" \
rather than "what the user should do next," rewrite it.

You will receive the reel's caption and its transcribed audio, and may also \
receive a visual timeline — on-screen text, slides, or notable visual \
changes extracted from the video's frames, by timestamp. Use all three \
together — they often carry different information (the transcript has \
spoken specifics like quantities and technique cues; the caption often has \
a place, product name, handle, or link the speaker never says aloud; the \
visual timeline can have exact names/text shown on screen but never said \
aloud, e.g. a slideshow of resource names). Treat the visual timeline as a \
source of specifics, not a video description to summarize. Any of the \
three may be marked unavailable/none; work with whichever is present.

When the visual timeline shows concrete specifics the transcript/caption \
never say out loud — an on-screen list of exact item names, job titles, \
prices, or addresses flashed briefly during a screen recording, for \
example — pull each one you can identify into its own details.key_points \
entry. The transcript already covering the general topic is not a reason \
to drop specifics that only ever appeared on screen; those are frequently \
the most valuable part of the reel precisely because they're never spoken.

## Classify into exactly one task_type
- action_item — the reel demonstrates a technique, exercise, routine, \
recipe, or habit the user could start doing. Use this for anything \
instructional or how-to, even if phrased casually.
- event_reminder — the reel names a specific date, deadline, launch, or \
time-bound event worth remembering or acting on by then.
- resource_reference — the reel recommends a specific book, product, tool, \
place, app, or piece of media worth saving or checking out later, and the \
content is not primarily instructional.
- content_idea — the reel is itself a format or idea the user might want to \
recreate as their own content. Only pick this when the reel is clearly \
about content creation, not general life advice.
- other — only when none of the above genuinely fit. Do not default here \
out of laziness; most reels are action_item or resource_reference.

## Make it actionable
- title: a short imperative instruction — what to do, not what the reel is \
about. ("Batch-cook the 3-ingredient pasta sauce this Sunday", never \
"Pasta sauce recipe reel.")
- details.description: the concrete next step(s), written as instructions \
to the user, in 1-3 sentences. Keep the reel's specifics (ingredients, \
numbers, names) — don't generalize them away.
- details.key_points: a short ordered list of concrete sub-steps or \
specifics to remember while doing the task (exact quantities, technique \
cues, a product name, an address) — not a restated summary of the reel's \
narrative. Never repeat a fact already stated in details.description in \
different words; every key_points entry must add information the \
description doesn't already contain.
- details.location / details.link: fill in only if the reel actually names \
a real place or URL/handle — never invent one.
- due_date: ISO 8601 (YYYY-MM-DD) only if the reel names an actual \
date/deadline; otherwise null.
- reminder_lead_days: only meaningful when due_date is set — otherwise 0. \
Decide how many days *before* due_date the user should be reminded, based \
on what the date actually requires of them:
  - 0 — the date itself is what the user needs to show up for or observe \
  (a livestream, a launch, an event happening that day). Reminding earlier \
  would just be noise.
  - 2 to 5 — due_date is a deadline that requires preparation beforehand \
  (an application, a submission, booking something, buying a gift) — the \
  user needs advance warning to actually act, not just find out on the day \
  it's due.
  Never exceed 7. Pick the smallest lead time that still gives the user a \
  real chance to act — don't pad it out of caution.
- comment_to_unlock_keyword: set this ONLY when the reel *explicitly* \
instructs the viewer to comment a specific word/phrase to receive \
something via DM (e.g. "comment YES and I'll send you the link", "comment \
'GUIDE' below for the freebie"). Extract the exact word/phrase to comment \
— not a paraphrase, the literal text the creator asked for. Null for every \
other reel, including ones that just ask viewers to comment generically \
("comment your thoughts!") without promising anything back via DM.

## When comment_to_unlock_keyword is set
The app follows the creator and posts that comment automatically the \
moment this task is generated — the user never has to do it themselves. \
So when comment_to_unlock_keyword is non-null, title and \
details.description must NEVER instruct the user to comment, follow, or \
DM anyone — that mechanic is already handled, mentioning it back to the \
user is both redundant and wrong (it reads as a to-do they still have to \
do). Instead, describe the actual underlying opportunity using every real \
specific already available from the transcript/caption/visual timeline: \
what it is, who it's for, concrete figures/positions/names. If the \
creator's DM reply is already present in the transcript/caption text \
(a previously-generated task being regenerated after the reply arrived), \
that reply is usually the real substance — center the task on it, not on \
the original "comment to unlock" pitch. Example: a reel promising \
internship application links after a comment should produce a title like \
"Apply for the announced internship programs" (using the company/program \
name if known) — never "Comment X to get the internship links."
"""


def _build_prompt(transcript_text: str, caption: str, visual_summary: str = "") -> str:
    caption_block = caption if caption else "(none provided)"
    transcript_block = transcript_text if transcript_text else "(no speech detected / transcript unavailable)"
    visual_block = visual_summary if visual_summary else "(none)"
    return (
        f"Reel caption:\n{caption_block}\n\n"
        f"Reel transcript:\n{transcript_block}\n\n"
        f"Visual timeline (on-screen content by timestamp):\n{visual_block}"
    )


async def generate_task_async(user_reel_id: str) -> None:
    """Per-(user, reel) task generation — not part of process_reel_async's
    pipeline, since each user brings their own Gemini key (Phase 0), so
    this can't be deduped across users the way download/audio/transcribe
    are on the shared Reel content."""
    user_reel = await UserReel.get(user_reel_id)
    if user_reel is None:
        logger.warning("generate_task: user_reel_id=%s not found", user_reel_id)
        return

    if await GeneratedTask.find_one(
        GeneratedTask.user_id == user_reel.user_id, GeneratedTask.reel_id == user_reel.reel_id
    ):
        return

    reel = await Reel.get(user_reel.reel_id)
    if reel is None or reel.status != "transcribed":
        logger.warning(
            "generate_task: reel %s not ready (status=%s)",
            user_reel.reel_id,
            reel.status if reel else None,
        )
        return

    secret = await CredentialService.get(user_reel.user_id, "gemini")
    if secret is None:
        user_reel.task_generation_status = "failed"
        user_reel.task_generation_error = "no Gemini key configured"
        await user_reel.save()
        return

    transcript_text = (reel.transcript_text or "").strip()
    caption = (reel.caption or "").strip()
    visual_summary = (reel.visual_summary or "").strip()
    if not transcript_text and not caption:
        # Visual timeline alone doesn't count as "sufficient" — it's a
        # supplementary source of specifics (Phase 13), not a substitute
        # for having any transcript or caption at all.
        user_reel.task_generation_status = "failed"
        user_reel.task_generation_error = "insufficient_content"
        await user_reel.save()
        return

    prompt = _build_prompt(transcript_text, caption, visual_summary)

    try:
        client = genai.Client(api_key=secret["api_key"])
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=TaskGenerationSchema,
            ),
        )
        parsed: TaskGenerationSchema | None = response.parsed
        if parsed is None:
            raise ValueError("Gemini returned no parseable structured output")
    except genai_errors.APIError as exc:
        if exc.code >= 500 or exc.code == 429:
            # Transient (overloaded/rate-limited) — re-raise so RQ's
            # Retry(max=3) on this job (set where it's enqueued) actually
            # retries it, instead of the previous behavior of swallowing
            # every Gemini error identically and marking the task
            # permanently failed on the first hiccup.
            logger.warning(
                "task generation transient error, will retry user_id=%s reel_id=%s error=%s",
                user_reel.user_id,
                user_reel.reel_id,
                exc,
            )
            raise
        logger.warning(
            "task generation failed user_id=%s reel_id=%s error=%s",
            user_reel.user_id,
            user_reel.reel_id,
            exc,
        )
        user_reel.task_generation_status = "failed"
        user_reel.task_generation_error = str(exc)
        await user_reel.save()
        return
    except Exception as exc:
        logger.warning(
            "task generation failed user_id=%s reel_id=%s error=%s",
            user_reel.user_id,
            user_reel.reel_id,
            exc,
        )
        user_reel.task_generation_status = "failed"
        user_reel.task_generation_error = str(exc)
        await user_reel.save()
        return

    due_date = None
    if parsed.due_date:
        try:
            due_date = datetime.fromisoformat(parsed.due_date)
        except ValueError:
            due_date = None

    # Defensive clamp — reminder_lead_days is untrusted model output; a
    # stray negative or absurd value shouldn't be able to schedule a
    # calendar reminder in the past or wildly early.
    reminder_lead_days = max(0, min(parsed.reminder_lead_days, 7)) if due_date else 0

    generated_task = GeneratedTask(
        user_id=user_reel.user_id,
        reel_id=user_reel.reel_id,
        task_type=parsed.task_type,
        title=parsed.title,
        details=parsed.details,
        due_date=due_date,
        reminder_lead_days=reminder_lead_days,
        raw_llm_response=response.text or "",
    )
    await generated_task.insert()

    user_reel.task_generation_status = "generated"
    user_reel.task_generation_error = None
    await user_reel.save()

    logger.info(
        "task generated user_id=%s reel_id=%s task_type=%s",
        user_reel.user_id,
        user_reel.reel_id,
        parsed.task_type,
    )

    # Phase 8: push to wherever the user's routing preference sends this
    # task_type (Notion today, more integrations later) — no-ops cleanly if
    # nothing is configured, so this is safe to enqueue unconditionally.
    get_queue().enqueue(push_task, str(generated_task.id))

    # Phase 9: reel-level, not per-user — trigger_comment_unlock's own
    # idempotency check means only the first user's share of this reel to
    # reach here actually follows/comments, and a failure here (e.g.
    # INSTAGRAM_SESSION_ID not configured) never fails this already-
    # successful task generation.
    if parsed.comment_to_unlock_keyword:
        await trigger_comment_unlock(reel, parsed.comment_to_unlock_keyword)


def generate_task(user_reel_id: str) -> None:
    """RQ job entrypoint — same shape as `app.workers.process_reel.process_reel`:
    a plain sync function so each invocation gets its own event loop and
    Motor client."""

    async def _run() -> None:
        await init_db()
        await generate_task_async(user_reel_id)

    asyncio.run(_run())

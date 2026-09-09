from datetime import datetime, timedelta, timezone

import pytest

from app.models.comment_unlock_request import CommentUnlockRequest
from app.models.generated_task import GeneratedTask, TaskDetails
from app.models.reel import Reel
from app.queue import get_queue
from app.services.instagram_private import InstagramPrivateError
from app.workers import comment_unlock as cu_module
from app.workers.comment_unlock import trigger_comment_unlock, try_fulfill_from_dm

pytestmark = pytest.mark.asyncio


def _msg(text: str, mid: str = "mid-1") -> dict:
    return {"mid": mid, "text": text}


def _template_msg(title: str, url: str | None, mid: str = "mid-1") -> dict:
    buttons = [{"type": "open_url", "url": url, "title": "Explore Now !"}] if url else []
    return {
        "mid": mid,
        "attachments": [
            {"type": "template", "payload": {"generic": {"elements": [{"title": title, "buttons": buttons}]}}}
        ],
    }


def _button_template_msg(url: str, mid: str = "mid-1") -> dict:
    # "button template" — buttons at the payload root, no generic.elements
    return {
        "mid": mid,
        "attachments": [
            {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": "As promised 👇",
                    "buttons": [{"type": "web_url", "url": url, "title": "Open"}],
                },
            }
        ],
    }


def _payload_url_msg(url: str, mid: str = "mid-1") -> dict:
    return {"mid": mid, "attachments": [{"type": "fallback", "payload": {"url": url}}]}


def _buried_url_msg(url: str, mid: str = "mid-1") -> dict:
    return {
        "mid": mid,
        "attachments": [{"type": "template", "payload": {"wrapper": {"deep": {"redirect": url}}}}],
    }


def _unsupported_msg(mid: str = "mid-1") -> dict:
    return {"mid": mid, "attachments": [{"type": "unsupported"}]}


def _patch_instagram(monkeypatch, follow_error=None, comment_error=None, calls=None):
    calls = calls if calls is not None else []

    async def _follow(username):
        calls.append(("follow", username))
        if follow_error is not None:
            raise follow_error

    async def _comment(url, text):
        calls.append(("comment", url, text))
        if comment_error is not None:
            raise comment_error

    monkeypatch.setattr(cu_module, "follow_user", _follow)
    monkeypatch.setattr(cu_module, "comment_on_reel", _comment)
    return calls


async def _make_reel(**overrides):
    fields = dict(
        reel_video_id="v1",
        url="https://www.instagram.com/reel/abc/",
        creator_username="creator1",
        status="transcribed",
    )
    fields.update(overrides)
    return await Reel(**fields).insert()


async def test_trigger_follows_comments_and_creates_request(app, monkeypatch):
    calls = _patch_instagram(monkeypatch)
    reel = await _make_reel()

    await trigger_comment_unlock(reel, "YES")

    assert ("follow", "creator1") in calls
    assert ("comment", reel.url, "YES") in calls

    request = await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == str(reel.id))
    assert request is not None
    assert request.status == "pending"
    assert request.creator_username == "creator1"
    assert request.followed_at is not None

    updated_reel = await Reel.get(reel.id)
    assert updated_reel.comment_unlock_status == "pending"
    assert updated_reel.comment_unlock_keyword == "YES"


async def test_trigger_is_idempotent_per_reel(app, monkeypatch):
    calls = _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()

    await trigger_comment_unlock(reel, "YES")

    assert calls == []  # never even attempted — a request already exists
    count = await CommentUnlockRequest.find(CommentUnlockRequest.reel_id == str(reel.id)).count()
    assert count == 1


async def test_trigger_skips_when_creator_username_missing(app, monkeypatch):
    calls = _patch_instagram(monkeypatch)
    reel = await _make_reel(creator_username=None)

    await trigger_comment_unlock(reel, "YES")

    assert calls == []
    updated_reel = await Reel.get(reel.id)
    assert updated_reel.comment_unlock_status == "failed"
    assert await CommentUnlockRequest.find(CommentUnlockRequest.reel_id == str(reel.id)).count() == 0


async def test_trigger_leaves_bot_following_when_comment_fails(app, monkeypatch):
    # No unfollow-cleanup on partial failure — unfollow isn't automated at
    # all (see the phase's Risks note), so this is the accepted trade-off.
    calls = _patch_instagram(monkeypatch, comment_error=InstagramPrivateError("boom"))
    reel = await _make_reel()

    await trigger_comment_unlock(reel, "YES")

    assert ("follow", "creator1") in calls
    assert not any(c[0] == "unfollow" for c in calls)
    updated_reel = await Reel.get(reel.id)
    assert updated_reel.comment_unlock_status == "failed"
    # No request left behind — next share of this reel can retry cleanly.
    assert await CommentUnlockRequest.find(CommentUnlockRequest.reel_id == str(reel.id)).count() == 0


async def test_trigger_does_not_attempt_comment_when_follow_fails(app, monkeypatch):
    calls = _patch_instagram(monkeypatch, follow_error=InstagramPrivateError("boom"))
    reel = await _make_reel()

    await trigger_comment_unlock(reel, "YES")

    assert ("follow", "creator1") in calls
    assert not any(c[0] == "comment" for c in calls)


async def test_fulfill_merges_reply_into_every_task_for_the_reel(app, monkeypatch):
    calls = _patch_instagram(monkeypatch)
    reel = await _make_reel()
    request = await CommentUnlockRequest(
        reel_id=str(reel.id), creator_username="creator1", keyword="YES"
    ).insert()
    task1 = await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t1",
        details=TaskDetails(description="original desc"),
        raw_llm_response="{}",
    ).insert()
    task2 = await GeneratedTask(
        user_id="user-2",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t2",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    await try_fulfill_from_dm(_msg("Here's the link: https://example.com/guide"))

    updated_task1 = await GeneratedTask.get(task1.id)
    updated_task2 = await GeneratedTask.get(task2.id)
    assert "original desc" in updated_task1.details.description
    assert "Here's the link" in updated_task1.details.description
    assert updated_task1.details.link == "https://example.com/guide"
    assert updated_task2.details.link == "https://example.com/guide"

    jobs = get_queue().jobs
    assert len(jobs) == 2
    assert {j.args[0] for j in jobs} == {str(task1.id), str(task2.id)}

    updated_request = await CommentUnlockRequest.get(request.id)
    assert updated_request.status == "fulfilled"
    assert updated_request.reply_text.startswith("Here's the link")
    assert updated_request.reply_message_id == "mid-1"
    assert not any(c[0] == "unfollow" for c in calls)  # unfollow isn't automated

    updated_reel = await Reel.get(reel.id)
    assert updated_reel.comment_unlock_status == "fulfilled"


async def test_fulfill_does_not_overwrite_an_existing_link(app, monkeypatch):
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()
    task = await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t1",
        details=TaskDetails(link="https://already-set.example.com"),
        raw_llm_response="{}",
    ).insert()

    await try_fulfill_from_dm(_msg("check https://new-link.example.com"))

    updated_task = await GeneratedTask.get(task.id)
    assert updated_task.details.link == "https://already-set.example.com"


async def test_fulfill_handles_template_attachment_from_dm_automation_tools(app, monkeypatch):
    # Confirmed against a real reply from a creator's DM-automation tool
    # (SuperProfile.bio) — the common shape for "comment X for DM" replies,
    # not an edge case: a Messenger-style card, not plain text.
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()
    task = await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t1",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    message = _template_msg(
        "Hi there!\nAs promised, here's the link! ⬇️",
        "https://prod.api.cosmofeed.com/api/adm/tm?url=https%3A%2F%2Fexample.com%2Fguide",
    )
    matched = await try_fulfill_from_dm(message)

    assert matched is True
    updated_task = await GeneratedTask.get(task.id)
    assert "As promised" in updated_task.details.description
    # The button's URL is taken directly, not regexed out of the title —
    # the title only shows the button's label, never the URL itself.
    assert updated_task.details.link == (
        "https://prod.api.cosmofeed.com/api/adm/tm?url=https%3A%2F%2Fexample.com%2Fguide"
    )


async def _task_for(reel):
    return await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t1",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()


@pytest.mark.parametrize(
    "make_message",
    [
        lambda: _button_template_msg("https://example.com/guide"),
        lambda: _payload_url_msg("https://example.com/guide"),
        lambda: _buried_url_msg("https://example.com/guide"),
    ],
    ids=["button-template", "payload-url", "buried-url"],
)
async def test_fulfill_extracts_link_from_varied_dm_shapes(app, monkeypatch, make_message):
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()
    task = await _task_for(reel)

    matched = await try_fulfill_from_dm(make_message())

    assert matched is True
    updated_task = await GeneratedTask.get(task.id)
    assert updated_task.details.link == "https://example.com/guide"


async def test_fulfill_stores_raw_reply_payload_on_request(app, monkeypatch):
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    request = await CommentUnlockRequest(
        reel_id=str(reel.id), creator_username="creator1", keyword="YES"
    ).insert()
    await _task_for(reel)
    message = _button_template_msg("https://example.com/guide")

    await try_fulfill_from_dm(message)

    updated = await CommentUnlockRequest.get(request.id)
    assert updated.reply_raw == message


async def test_unparseable_dm_does_not_consume_pending_request_and_warns(app, monkeypatch, caplog):
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()

    with caplog.at_level("WARNING"):
        matched = await try_fulfill_from_dm(_unsupported_msg())

    assert matched is False
    request = await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == str(reel.id))
    assert request.status == "pending"
    assert "unparseable" in caplog.text


async def test_fulfill_rejects_non_http_scheme_in_template_button_url(app, monkeypatch):
    # The button's `url` comes from whoever DMs the bot, not necessarily
    # the real creator (FIFO matching is best-effort) — a javascript:/data:
    # scheme must never land in details.link.
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()
    task = await GeneratedTask(
        user_id="user-1",
        reel_id=str(reel.id),
        task_type="resource_reference",
        title="t1",
        details=TaskDetails(),
        raw_llm_response="{}",
    ).insert()

    message = _template_msg("click here", "javascript:alert(document.cookie)")
    matched = await try_fulfill_from_dm(message)

    assert matched is True
    updated_task = await GeneratedTask.get(task.id)
    assert updated_task.details.link is None


async def test_try_fulfill_ignores_unrecognized_message_shapes(app, monkeypatch):
    _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()

    # No text, no template attachment — e.g. an image/reel share reply.
    matched = await try_fulfill_from_dm({"mid": "mid-1", "attachments": [{"type": "image"}]})

    assert matched is False
    request = await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == str(reel.id))
    assert request.status == "pending"


async def test_try_fulfill_matches_oldest_pending_request_fifo(app, monkeypatch):
    _patch_instagram(monkeypatch)
    reel_a = await _make_reel(reel_video_id="a", creator_username="creator-a")
    reel_b = await _make_reel(reel_video_id="b", creator_username="creator-b")
    now = datetime.now(timezone.utc)
    await CommentUnlockRequest(
        reel_id=str(reel_a.id), creator_username="creator-a", keyword="YES", commented_at=now
    ).insert()
    await CommentUnlockRequest(
        reel_id=str(reel_b.id),
        creator_username="creator-b",
        keyword="YES",
        commented_at=now + timedelta(minutes=5),
    ).insert()

    matched = await try_fulfill_from_dm(_msg("here you go"))

    assert matched is True
    request_a = await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == str(reel_a.id))
    request_b = await CommentUnlockRequest.find_one(CommentUnlockRequest.reel_id == str(reel_b.id))
    assert request_a.status == "fulfilled"
    assert request_b.status == "pending"


async def test_try_fulfill_returns_false_when_nothing_pending(app):
    matched = await try_fulfill_from_dm(_msg("random text"))
    assert matched is False


async def test_try_fulfill_is_idempotent_on_redelivered_message(app, monkeypatch):
    calls = _patch_instagram(monkeypatch)
    reel = await _make_reel()
    await CommentUnlockRequest(reel_id=str(reel.id), creator_username="creator1", keyword="YES").insert()

    first = await try_fulfill_from_dm(_msg("here you go"))
    calls.clear()
    second = await try_fulfill_from_dm(_msg("here you go"))

    assert first is True
    assert second is True
    assert calls == []  # second call is a no-op, not a re-fulfillment
    assert await GeneratedTask.find(GeneratedTask.reel_id == str(reel.id)).count() == 0


async def test_try_fulfill_expires_stale_pending_and_moves_to_next(app, monkeypatch):
    _patch_instagram(monkeypatch)
    stale_reel = await _make_reel(reel_video_id="stale", creator_username="stale-creator")
    fresh_reel = await _make_reel(reel_video_id="fresh", creator_username="fresh-creator")
    stale_time = datetime.now(timezone.utc) - timedelta(hours=100)
    await CommentUnlockRequest(
        reel_id=str(stale_reel.id),
        creator_username="stale-creator",
        keyword="YES",
        commented_at=stale_time,
    ).insert()
    await CommentUnlockRequest(
        reel_id=str(fresh_reel.id), creator_username="fresh-creator", keyword="YES"
    ).insert()

    matched = await try_fulfill_from_dm(_msg("here you go"))

    assert matched is True
    stale_request = await CommentUnlockRequest.find_one(
        CommentUnlockRequest.reel_id == str(stale_reel.id)
    )
    fresh_request = await CommentUnlockRequest.find_one(
        CommentUnlockRequest.reel_id == str(fresh_reel.id)
    )
    assert stale_request.status == "expired"
    assert fresh_request.status == "fulfilled"

    stale_reel_updated = await Reel.get(stale_reel.id)
    assert stale_reel_updated.comment_unlock_status == "expired"

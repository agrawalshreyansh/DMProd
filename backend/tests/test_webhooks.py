import json
from datetime import datetime, timedelta, timezone

import pytest

from app.api import webhooks as webhooks_api
from app.models.instagram_account import InstagramAccount
from app.models.pending_verification import PendingVerification
from app.models.reel import Reel
from app.models.webhook_event_log import WebhookEventLog
from tests.conftest import sign_payload


def _text_message_payload(sender_id: str, text: str) -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "17841400000000000",
                "time": 1700000000,
                "messaging": [
                    {
                        "sender": {"id": sender_id},
                        "recipient": {"id": "17841400000000000"},
                        "timestamp": 1700000000123,
                        "message": {"mid": "text-message-id", "text": text},
                    }
                ],
            }
        ],
    }

pytestmark = pytest.mark.asyncio


async def test_get_handshake_returns_challenge_when_token_matches(client):
    resp = await client.get(
        "/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


async def test_get_handshake_rejects_wrong_token(client):
    resp = await client.get(
        "/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 403


async def test_post_with_valid_signature_is_accepted_and_logged(client, instagram_webhook_payload):
    body = json.dumps(instagram_webhook_payload).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign_payload(body),
        },
    )
    assert resp.status_code == 200

    logs = await WebhookEventLog.find_all().to_list()
    assert len(logs) == 1
    assert logs[0].raw_payload == instagram_webhook_payload


async def test_post_with_invalid_signature_is_rejected(client, instagram_webhook_payload):
    body = json.dumps(instagram_webhook_payload).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert resp.status_code == 401
    assert await WebhookEventLog.find_all().to_list() == []


async def test_post_with_missing_signature_is_rejected(client, instagram_webhook_payload):
    body = json.dumps(instagram_webhook_payload).encode()
    resp = await client.post(
        "/webhooks/instagram", content=body, headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401
    assert await WebhookEventLog.find_all().to_list() == []


async def test_reel_from_linked_sender_is_stored_against_the_right_user(
    client, instagram_webhook_payload
):
    await InstagramAccount(
        user_id="user-abc", ig_user_id="1234567890", username="alex"
    ).insert()

    body = json.dumps(instagram_webhook_payload).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200

    reels = await Reel.find_all().to_list()
    assert len(reels) == 1
    assert reels[0].user_id == "user-abc"
    assert reels[0].sender_ig_id == "1234567890"
    assert reels[0].reel_video_id == "17871182922633701"
    assert reels[0].caption == "A reel about something"


async def test_reel_from_unlinked_sender_is_not_stored(client, instagram_webhook_payload):
    body = json.dumps(instagram_webhook_payload).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200
    assert await Reel.find_all().to_list() == []


async def test_redelivered_event_does_not_duplicate_the_reel(client, instagram_webhook_payload):
    await InstagramAccount(
        user_id="user-abc", ig_user_id="1234567890", username="alex"
    ).insert()

    body = json.dumps(instagram_webhook_payload).encode()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)}

    await client.post("/webhooks/instagram", content=body, headers=headers)
    resp = await client.post("/webhooks/instagram", content=body, headers=headers)

    assert resp.status_code == 200
    assert len(await Reel.find_all().to_list()) == 1


async def test_dm_with_valid_code_links_the_sender_and_fetches_their_username(
    client, monkeypatch
):
    await PendingVerification(
        user_id="user-abc",
        code="ABC123",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    ).insert()

    async def fake_fetch_username(ig_user_id):
        assert ig_user_id == "1234567890"
        return "realuser"

    monkeypatch.setattr(webhooks_api, "fetch_username", fake_fetch_username)

    body = json.dumps(_text_message_payload("1234567890", "abc123")).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200

    account = await InstagramAccount.find_one(InstagramAccount.ig_user_id == "1234567890")
    assert account is not None
    assert account.user_id == "user-abc"
    assert account.username == "realuser"

    assert await PendingVerification.find_one(PendingVerification.code == "ABC123") is None


async def test_dm_with_valid_code_links_even_if_username_lookup_fails(client, monkeypatch):
    await PendingVerification(
        user_id="user-abc",
        code="ABC123",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    ).insert()

    async def failing_fetch_username(ig_user_id):
        raise RuntimeError("graph api down")

    monkeypatch.setattr(webhooks_api, "fetch_username", failing_fetch_username)

    body = json.dumps(_text_message_payload("1234567890", "ABC123")).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200

    account = await InstagramAccount.find_one(InstagramAccount.ig_user_id == "1234567890")
    assert account is not None
    assert account.username == ""


async def test_dm_with_expired_code_does_not_link(client):
    await PendingVerification(
        user_id="user-abc",
        code="ABC123",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ).insert()

    body = json.dumps(_text_message_payload("1234567890", "ABC123")).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200
    assert await InstagramAccount.find_all().to_list() == []


async def test_dm_with_unknown_code_does_not_link(client):
    body = json.dumps(_text_message_payload("1234567890", "NOTREAL")).encode()
    resp = await client.post(
        "/webhooks/instagram",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign_payload(body)},
    )
    assert resp.status_code == 200
    assert await InstagramAccount.find_all().to_list() == []

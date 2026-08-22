import json

import pytest

from app.models.webhook_event_log import WebhookEventLog
from tests.conftest import sign_payload

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

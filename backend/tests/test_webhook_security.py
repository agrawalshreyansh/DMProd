from app.services.webhook_security import verify_signature

SECRET = "test-meta-app-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    import hashlib
    import hmac

    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_passes():
    body = b'{"hello":"world"}'
    assert verify_signature(body, _sign(body)) is True


def test_tampered_body_rejected():
    body = b'{"hello":"world"}'
    signature = _sign(body)
    tampered = b'{"hello":"mallory"}'
    assert verify_signature(tampered, signature) is False


def test_missing_header_rejected():
    body = b'{"hello":"world"}'
    assert verify_signature(body, None) is False


def test_wrong_secret_rejected():
    body = b'{"hello":"world"}'
    signature = _sign(body, secret="not-the-real-secret")
    assert verify_signature(body, signature) is False


def test_missing_sha256_prefix_rejected():
    body = b'{"hello":"world"}'
    # a raw hex digest without the "sha256=" prefix Meta always sends
    bare = _sign(body).removeprefix("sha256=")
    assert verify_signature(body, bare) is False


def test_empty_header_rejected():
    body = b'{"hello":"world"}'
    assert verify_signature(body, "") is False

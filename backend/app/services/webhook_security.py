import hashlib
import hmac

from app.config import settings


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify Meta's X-Hub-Signature-256 header against the raw request body.

    Constant-time compare on purpose — this gates a public endpoint.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(settings.meta_app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)

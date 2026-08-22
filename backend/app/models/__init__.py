from app.models.instagram_account import InstagramAccount
from app.models.pending_verification import PendingVerification
from app.models.preference import Preference
from app.models.reel import Reel
from app.models.user import User
from app.models.user_credential import UserCredential
from app.models.webhook_event_log import WebhookEventLog

document_models = [
    User,
    UserCredential,
    Preference,
    WebhookEventLog,
    InstagramAccount,
    Reel,
    PendingVerification,
]

__all__ = [
    "User",
    "UserCredential",
    "Preference",
    "WebhookEventLog",
    "InstagramAccount",
    "Reel",
    "PendingVerification",
    "document_models",
]

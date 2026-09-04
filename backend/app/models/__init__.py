from app.models.comment_unlock_request import CommentUnlockRequest
from app.models.generated_task import GeneratedTask
from app.models.instagram_account import InstagramAccount
from app.models.integration import Integration
from app.models.pending_verification import PendingVerification
from app.models.preference import Preference
from app.models.push_log import PushLog
from app.models.reel import Reel
from app.models.user import User
from app.models.user_credential import UserCredential
from app.models.user_reel import UserReel
from app.models.webhook_event_log import WebhookEventLog

document_models = [
    User,
    UserCredential,
    Preference,
    WebhookEventLog,
    InstagramAccount,
    Reel,
    PendingVerification,
    UserReel,
    GeneratedTask,
    Integration,
    PushLog,
    CommentUnlockRequest,
]

__all__ = [
    "User",
    "UserCredential",
    "Preference",
    "WebhookEventLog",
    "InstagramAccount",
    "Reel",
    "PendingVerification",
    "UserReel",
    "GeneratedTask",
    "Integration",
    "PushLog",
    "CommentUnlockRequest",
    "document_models",
]

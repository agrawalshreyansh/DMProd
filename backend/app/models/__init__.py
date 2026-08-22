from app.models.preference import Preference
from app.models.user import User
from app.models.user_credential import UserCredential
from app.models.webhook_event_log import WebhookEventLog

document_models = [User, UserCredential, Preference, WebhookEventLog]

__all__ = ["User", "UserCredential", "Preference", "WebhookEventLog", "document_models"]

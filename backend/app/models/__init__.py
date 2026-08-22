from app.models.preference import Preference
from app.models.user import User
from app.models.user_credential import UserCredential

document_models = [User, UserCredential, Preference]

__all__ = ["User", "UserCredential", "Preference", "document_models"]

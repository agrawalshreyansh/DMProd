from datetime import datetime, timezone
from typing import Any, Literal

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

# ponytail: only "notion" exists (Phase 8 scope is Notion-only). Add
# "google_calendar"/"google_sheet" here when those land — dispatch in
# app/workers/push.py stays a plain if/elif per type, no plugin registry
# needed for this few entries.
IntegrationType = Literal["notion"]


class Integration(Document):
    """Config/status only — no token field. The actual secret lives in
    `user_credentials` (via `CredentialService`), keyed by provider name."""

    user_id: str
    type: IntegrationType
    target_config: dict[str, Any] = Field(default_factory=dict)
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enabled: bool = True

    class Settings:
        name = "integrations"
        indexes = [
            IndexModel([("user_id", 1), ("type", 1)], unique=True),
        ]

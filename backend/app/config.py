from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "dmprod"
    redis_url: str = ""
    app_encryption_key: str
    jwt_secret: str
    jwt_expire_minutes: int = 10080
    cors_origin: str = "http://localhost:3000"
    meta_app_secret: str
    webhook_verify_token: str
    instagram_bot_access_token: str
    # Worker-only. Hosted Whisper via Groq (OpenAI-compatible audio API).
    # `whisper-large-v3` over `-turbo` for better multilingual accuracy —
    # Hinglish (Hindi/English code-switched) audio is the primary use case.
    groq_api_key: str = ""
    groq_whisper_model: str = "whisper-large-v3"
    google_client_id: str = ""
    google_client_secret: str = ""
    instagram_session_id: str = ""
    # Phase 13 (visual analysis) — deliberately app-level, not per-user: this
    # step runs inside the shared content pipeline (process_reel), which has
    # no user context to pull a Gemini key from (same reason Phase 6 chose
    # whisper.cpp over Gemini for transcription). Empty disables the feature
    # entirely (visual_processing_status="skipped"), Phase 7's per-user task
    # generation is unaffected either way.
    visual_analysis_gemini_api_key: str = ""


settings = Settings()

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


settings = Settings()

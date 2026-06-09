import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/placement_sentinel")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    AES_SECRET_KEY: str = Field(default="")
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/callback")
    WEBHOOK_AUDIENCE: str = Field(default="http://localhost:8000/api/v1/webhook")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.AES_SECRET_KEY:
            # Dynamic key generation is useful for local tests, but we log a warning since data
            # won't persist across restarts if the key changes.
            from cryptography.fernet import Fernet
            self.AES_SECRET_KEY = Fernet.generate_key().decode()
            logger.warning(
                "AES_SECRET_KEY was not set in the environment. "
                "Generated a dynamic key. Decryption will fail on server restart!"
            )

settings = Settings()

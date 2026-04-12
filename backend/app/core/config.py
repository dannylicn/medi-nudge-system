import hashlib
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./medi_nudge.db"
    JWT_SECRET_KEY: str = "changeme-replace-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OPENAI_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o"
    ELEVENLABS_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    WARNING_DAYS: int = 3
    ESCALATION_DAYS: int = 14
    MAX_NUDGE_ATTEMPTS: int = 3
    MISSED_DOSE_ESCALATION_THRESHOLD: int = 3  # consecutive misses before caregiver notified
    MEDIA_STORAGE_PATH: str = "./media"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def hash_sha256(value: str) -> str:
    """Hash a sensitive string with SHA-256. Never store the original."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

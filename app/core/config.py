"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "PepperFlow AI"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pepperflow"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Workflow
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.0
    HITL_TIMEOUT_SECONDS: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

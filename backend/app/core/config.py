from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/antibody"
    )
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "batch-task-queue"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

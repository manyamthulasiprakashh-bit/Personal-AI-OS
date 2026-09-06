from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = Field(default="Personal AI-OS")
    environment: str = Field(default="development")
    api_v1_str: str = Field(default="/api")
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = Field(default="INFO")
    database_url: str = Field(
        default="postgresql+psycopg://personal_ai_os:personal_ai_os@localhost:5432/personal_ai_os"
    )
    secret_key: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = Field(default=60)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return self.backend_cors_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

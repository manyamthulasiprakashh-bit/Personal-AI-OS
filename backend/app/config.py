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
    development_user_email: str = Field(default="")
    job_provider: str = Field(default="mock")
    stock_provider: str = Field(default="mock")
    alphavantage_api_key: str = Field(default="")
    alphavantage_api_base_url: str = Field(default="https://www.alphavantage.co/query")
    stock_timeout_seconds: int = Field(default=10, ge=1, le=60)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="")
    openai_timeout_seconds: int = Field(default=30, ge=1, le=300)
    openai_max_output_tokens: int = Field(default=1000, ge=64, le=4096)
    job_analysis_max_input_chars: int = Field(default=20000, ge=1000, le=100000)
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

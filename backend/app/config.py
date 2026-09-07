from functools import lru_cache

from typing import Literal

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
    auth_mode: str = Field(default="development")
    auth0_issuer: str = Field(default="")
    auth0_client_id: str = Field(default="")
    auth0_client_secret: str = Field(default="")
    auth0_audience: str = Field(default="")
    auth0_redirect_uri: str = Field(default="http://localhost:8000/auth/callback")
    auth_frontend_redirect_uri: str = Field(default="http://localhost:3000")
    auth_session_cookie_name: str = Field(default="personal_ai_os_session")
    auth_state_cookie_name: str = Field(default="personal_ai_os_auth_state")
    auth_cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax")
    auth_session_ttl_seconds: int = Field(default=28800, ge=300, le=2592000)
    auth_state_ttl_seconds: int = Field(default=600, ge=60, le=1800)
    job_provider: str = Field(default="mock")
    stock_provider: str = Field(default="mock")
    alphavantage_api_key: str = Field(default="")
    alphavantage_api_base_url: str = Field(default="https://www.alphavantage.co/query")
    stock_timeout_seconds: int = Field(default=10, ge=1, le=60)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="")
    openai_timeout_seconds: int = Field(default=30, ge=1, le=300)
    openai_max_output_tokens: int = Field(default=1000, ge=64, le=4096)
    agent_planner_provider: str = Field(default="rule_based")
    agent_planner_model: str = Field(default="")
    agent_planner_timeout_seconds: int = Field(default=30, ge=1, le=300)
    agent_planner_max_output_tokens: int = Field(default=512, ge=64, le=4096)
    agent_planner_local_base_url: str = Field(default="http://localhost:11434")
    agent_planner_local_timeout_seconds: int = Field(default=30, ge=1, le=300)
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

    def validate_production_settings(self) -> None:
        if "*" in self.backend_cors_origins:
            raise ValueError("wildcard CORS origins are not allowed")
        if self.environment.lower() != "production":
            return self
        if self.database_url == (
            "postgresql+psycopg://personal_ai_os:personal_ai_os@localhost:5432/personal_ai_os"
        ):
            raise ValueError("production DATABASE_URL must be configured")
        required = {
            "DATABASE_URL": self.database_url,
            "AUTH0_ISSUER": self.auth0_issuer,
            "AUTH0_CLIENT_ID": self.auth0_client_id,
            "AUTH0_CLIENT_SECRET": self.auth0_client_secret,
            "AUTH0_REDIRECT_URI": self.auth0_redirect_uri,
            "AUTH_FRONTEND_REDIRECT_URI": self.auth_frontend_redirect_uri,
            "SECRET_KEY": self.secret_key,
            "AGENT_PLANNER_MODEL": self.agent_planner_model,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"production settings missing: {', '.join(missing)}")
        if self.auth_mode != "oidc":
            raise ValueError("production authentication requires AUTH_MODE=oidc")
        if self.secret_key == "change-me-in-production":
            raise ValueError("production SECRET_KEY must be changed")
        if not self.auth0_redirect_uri.startswith("https://"):
            raise ValueError("production AUTH0_REDIRECT_URI must use HTTPS")
        if not self.auth_frontend_redirect_uri.startswith("https://"):
            raise ValueError("production AUTH_FRONTEND_REDIRECT_URI must use HTTPS")
        if self.auth_cookie_samesite == "none" and not self.auth0_redirect_uri.startswith(
            "https://"
        ):
            raise ValueError("SameSite=None requires HTTPS")
        if self.agent_planner_provider != "llm":
            raise ValueError("production AGENT_PLANNER_PROVIDER must be llm")
        if not self.openai_api_key.strip():
            raise ValueError("production OPENAI_API_KEY is required for the hosted planner")
        if not self.backend_cors_origins:
            raise ValueError("production BACKEND_CORS_ORIGINS must contain an origin")
        if any(not origin.startswith("https://") for origin in self.backend_cors_origins):
            raise ValueError("production CORS origins must use HTTPS")


@lru_cache
def get_settings() -> Settings:
    return Settings()

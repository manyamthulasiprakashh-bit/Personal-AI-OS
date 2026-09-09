from __future__ import annotations

import pytest

from app.config import Settings


def test_production_settings_require_oidc_and_hosted_planner() -> None:
    settings = Settings(environment="production")

    with pytest.raises(ValueError, match="production DATABASE_URL"):
        settings.validate_production_settings()


def test_production_settings_reject_wildcard_cors() -> None:
    settings = Settings(backend_cors_origins=["*"])

    with pytest.raises(ValueError, match="wildcard CORS"):
        settings.validate_production_settings()


def _base_production_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "environment": "production",
        "database_url": "postgresql+psycopg://user:pass@prod-host:5432/db",
        "auth_mode": "oidc",
        "auth0_issuer": "https://example.auth0.com/",
        "auth0_client_id": "client-id",
        "auth0_client_secret": "client-secret",
        "auth0_redirect_uri": "https://api.example.com/auth/callback",
        "auth_frontend_redirect_uri": "https://app.example.com",
        "secret_key": "a-real-production-secret",
        "backend_cors_origins": ["https://app.example.com"],
        "openai_api_key": "",
        "agent_planner_provider": "rule_based",
        "agent_planner_model": "",
    }
    kwargs.update(overrides)
    return kwargs


def test_production_rule_based_planner_does_not_require_openai_key_or_model() -> None:
    settings = Settings(**_base_production_kwargs(agent_planner_provider="rule_based"))

    settings.validate_production_settings()


def test_production_llm_planner_requires_openai_key() -> None:
    settings = Settings(
        **_base_production_kwargs(agent_planner_provider="llm", agent_planner_model="gpt-test")
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.validate_production_settings()


def test_production_llm_planner_requires_agent_planner_model() -> None:
    settings = Settings(
        **_base_production_kwargs(agent_planner_provider="llm", openai_api_key="sk-test")
    )

    with pytest.raises(ValueError, match="AGENT_PLANNER_MODEL"):
        settings.validate_production_settings()


def test_production_rejects_local_planner_provider() -> None:
    settings = Settings(**_base_production_kwargs(agent_planner_provider="local"))

    with pytest.raises(ValueError, match="AGENT_PLANNER_PROVIDER must be rule_based or llm"):
        settings.validate_production_settings()

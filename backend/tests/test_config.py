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

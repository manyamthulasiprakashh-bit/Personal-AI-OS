from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine

from app.agentic.planner import RuleBasedPlanner
from app.providers.factory import get_agent_planner_provider
from app.main import app
from app.database.session import Base


@pytest.fixture(autouse=True)
def reset_test_db() -> None:
    if os.getenv("ENVIRONMENT", "").lower() != "test":
        return

    engine = create_engine(
        "sqlite+pysqlite:////tmp/personal_ai_os_test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def deterministic_agent_planner() -> None:
    app.dependency_overrides[get_agent_planner_provider] = RuleBasedPlanner
    yield
    app.dependency_overrides.pop(get_agent_planner_provider, None)

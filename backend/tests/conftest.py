from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine

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

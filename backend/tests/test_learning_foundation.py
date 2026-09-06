from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import dependencies
from app.database.session import SessionLocal
from app.models.learning import LearningResource
from app.models.user import User
from app.repositories.learning import LearningRepository
from app.schemas.learning import (
    LearningGoalCreate,
    LearningResourceCreate,
    LearningSessionCreate,
)
from app.services.learning_service import LearningService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def users(db):
    user_a = User(email="learning-a@example.com", full_name="Learning A")
    user_b = User(email="learning-b@example.com", full_name="Learning B")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    return user_a, user_b


def test_current_user_resolves_configured_active_user(db, users, monkeypatch):
    user_a, _ = users
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(development_user_email=user_a.email),
    )

    current_user = dependencies.get_current_user(db)

    assert current_user.id == user_a.id
    assert current_user.email == user_a.email


def test_current_user_missing_configured_user_fails(db, monkeypatch):
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(development_user_email="missing@example.com"),
    )

    with pytest.raises(HTTPException, match="does not exist"):
        dependencies.get_current_user(db)


def test_current_user_inactive_configured_user_fails(db, users, monkeypatch):
    user_a, _ = users
    user_a.is_active = False
    db.commit()
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(development_user_email=user_a.email),
    )

    with pytest.raises(HTTPException, match="inactive"):
        dependencies.get_current_user(db)


def test_learning_goals_and_progress_are_owner_scoped(db, users):
    user_a, user_b = users
    service_a = LearningService(db, user_a.id)
    service_b = LearningService(db, user_b.id)
    goal = service_a.create_goal(LearningGoalCreate(title="Python", priority="high"))

    assert service_a.get_goal(goal.id).id == goal.id
    with pytest.raises(HTTPException) as error:
        service_b.get_goal(goal.id)
    assert error.value.status_code == 404

    session = LearningSessionCreate(
        goal_id=goal.id,
        started_at=datetime(2026, 9, 6, 9, 0),
        duration_minutes=45,
    )
    with pytest.raises(HTTPException) as error:
        service_b.create_session(session)
    assert error.value.status_code == 404

    service_a.create_session(session)
    assert service_a.get_progress().total_minutes == 45
    assert service_b.get_progress().total_sessions == 0


def test_resources_are_owner_scoped(db, users):
    user_a, user_b = users
    service_a = LearningService(db, user_a.id)
    service_b = LearningService(db, user_b.id)
    goal = service_a.create_goal(LearningGoalCreate(title="Databases"))
    resource = service_a.create_resource(
        LearningResourceCreate(goal_id=goal.id, title="SQL guide", url="https://example.com")
    )

    assert resource.user_id == user_a.id
    with pytest.raises(HTTPException) as error:
        service_b.create_resource(
            LearningResourceCreate(goal_id=goal.id, title="Cross-user resource")
        )
    assert error.value.status_code == 404
    assert db.query(LearningResource).filter(LearningResource.user_id == user_b.id).count() == 0


def test_empty_learning_data_has_deterministic_progress(db, users):
    progress = LearningService(db, users[0].id).get_progress()

    assert progress.model_dump() == {
        "goal_id": None,
        "total_goals": 0,
        "active_goals": 0,
        "completed_goals": 0,
        "total_sessions": 0,
        "total_minutes": 0,
    }


def test_invalid_session_duration_is_rejected():
    with pytest.raises(ValueError):
        LearningSessionCreate(
            goal_id="goal-id",
            started_at=datetime(2026, 9, 6, 9, 0),
            duration_minutes=0,
        )


def test_learning_create_schemas_reject_request_user_id():
    with pytest.raises(ValueError):
        LearningGoalCreate(title="Unauthorized ownership", user_id="other-user")


def test_repository_queries_require_owner_scope(db, users):
    user_a, user_b = users
    repository_a = LearningRepository(db, user_a.id)
    repository_b = LearningRepository(db, user_b.id)
    goal = repository_a.create_goal({"title": "Scoped goal"})

    assert repository_a.get_goal(goal.id) is not None
    assert repository_b.get_goal(goal.id) is None
    assert repository_b.get_progress()["total_goals"] == 0

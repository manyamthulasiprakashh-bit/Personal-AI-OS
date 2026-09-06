from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agents.learning.agent import LearningAgent
from app.api.dependencies import CurrentUser, get_current_user
from app.api.routes.learning import get_learning_agent, get_learning_service
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User
from app.providers.mock import MockProvider
from app.schemas.learning import (
    LearningAgentResponse,
    LearningGoalCreate,
    LearningProgress,
    LearningSessionCreate,
)
from app.services.learning_service import LearningService


class StubAgent:
    def __init__(self):
        self.goal_id = None

    def recommend(self, goal_id=None):
        self.goal_id = goal_id
        return LearningAgentResponse(
            progress=LearningProgress(
                goal_id=goal_id,
                total_goals=0,
                active_goals=0,
                completed_goals=0,
                total_sessions=0,
                total_minutes=0,
            ),
            recommendation={
                "summary": "No learning goals have been created yet.",
                "observations": ["There is no stored learning activity to review."],
                "recommendations": ["Create a learning goal to begin tracking progress."],
                "next_steps": ["Define one focused learning goal and its target outcome."],
            },
        )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_learning_service_dependency_uses_current_user(db):
    current_user = CurrentUser(id="user-123", email="user@example.com")

    service = get_learning_service(db, current_user)

    assert service.repository.user_id == current_user.id


def test_create_learning_goal_returns_typed_response(client, db):
    user = User(email="goal-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    try:
        response = client.post(
            "/api/learning/goals",
            json={
                "title": "Python",
                "description": "Build stronger Python fundamentals",
                "priority": "high",
                "target_date": "2026-12-31",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Python"
    assert body["user_id"] == user.id
    assert body["priority"] == "high"


def test_learning_goal_list_and_get_are_owner_scoped(client, db):
    owner = User(email="goal-list-owner@example.com")
    other = User(email="goal-list-other@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    owner_goal = LearningService(db, owner.id).create_goal(LearningGoalCreate(title="Owner goal"))
    other_goal = LearningService(db, other.id).create_goal(LearningGoalCreate(title="Other goal"))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(owner.id, owner.email)
    try:
        listed = client.get("/api/learning/goals")
        owned = client.get(f"/api/learning/goals/{owner_goal.id}")
        cross_user = client.get(f"/api/learning/goals/{other_goal.id}")
        missing = client.get("/api/learning/goals/00000000-0000-0000-0000-000000000000")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert listed.status_code == 200
    assert [goal["id"] for goal in listed.json()] == [owner_goal.id]
    assert owned.status_code == 200
    assert owned.json()["title"] == "Owner goal"
    assert cross_user.status_code == 404
    assert missing.status_code == 404


@pytest.mark.parametrize("field", ["user_id", "unexpected"])
def test_learning_goal_create_rejects_client_controlled_fields(client, field):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        "goal-validation-user", "goal-validation@example.com"
    )
    try:
        response = client.post("/api/learning/goals", json={"title": "Goal", field: "bad"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422


def test_created_goal_appears_in_progress(client, db):
    user = User(email="goal-progress-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    try:
        create_response = client.post("/api/learning/goals", json={"title": "Progress goal"})
        progress_response = client.get("/api/learning/progress")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert create_response.status_code == 201
    assert progress_response.status_code == 200
    assert progress_response.json()["total_goals"] == 1
    assert progress_response.json()["active_goals"] == 1


def test_learning_endpoint_returns_typed_progress_and_recommendation(client):
    agent = StubAgent()
    app.dependency_overrides[get_learning_agent] = lambda: agent
    try:
        response = client.post("/api/learning/agent/recommend", json={})
    finally:
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 200, response.text
    assert response.json()["progress"]["total_minutes"] == 0
    assert response.json()["recommendation"]["next_steps"]


@pytest.mark.parametrize("field", ["user_id", "tool_name", "provider"])
def test_learning_endpoint_rejects_client_controlled_fields(client, field):
    app.dependency_overrides[get_learning_agent] = lambda: StubAgent()
    try:
        response = client.post("/api/learning/agent/recommend", json={field: "not-authoritative"})
    finally:
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 422


def test_learning_endpoint_delegates_to_agent(client):
    agent = StubAgent()
    app.dependency_overrides[get_learning_agent] = lambda: agent
    try:
        response = client.post("/api/learning/agent/recommend", json={"goal_id": "goal-123"})
    finally:
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 200
    assert agent.goal_id == "goal-123"


def test_learning_endpoint_maps_provider_failure_to_503(client):
    class FailingProvider:
        def generate_learning_recommendation(self, progress):
            raise RuntimeError("provider unavailable")

    agent = LearningAgent(
        SimpleNamespace(
            get_progress=lambda goal_id=None: LearningProgress(
                goal_id=goal_id,
                total_goals=0,
                active_goals=0,
                completed_goals=0,
                total_sessions=0,
                total_minutes=0,
            )
        ),
        FailingProvider(),
    )
    app.dependency_overrides[get_learning_agent] = lambda: agent
    try:
        response = client.post("/api/learning/agent/recommend", json={})
    finally:
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 503


def test_cross_user_goal_id_returns_404(client, db):
    user_a = User(email="api-a@example.com")
    user_b = User(email="api-b@example.com")
    db.add_all([user_a, user_b])
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)
    goal = LearningService(db, user_a.id).create_goal(LearningGoalCreate(title="Private goal"))
    service_b = LearningService(db, user_b.id)
    app.dependency_overrides[get_learning_agent] = lambda: LearningAgent(service_b, MockProvider())
    try:
        response = client.post("/api/learning/agent/recommend", json={"goal_id": goal.id})
    finally:
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 404


def test_create_learning_session_returns_typed_response(client, db):
    user = User(email="session-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    goal = LearningService(db, user.id).create_goal(LearningGoalCreate(title="Python"))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    try:
        response = client.post(
            "/api/learning/sessions",
            json={
                "goal_id": goal.id,
                "started_at": "2026-09-06T09:00:00Z",
                "ended_at": "2026-09-06T09:45:00Z",
                "duration_minutes": 45,
                "notes": "Reviewed SQL joins",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["goal_id"] == goal.id
    assert body["user_id"] == user.id
    assert body["duration_minutes"] == 45
    assert body["notes"] == "Reviewed SQL joins"


def test_create_learning_session_rejects_unknown_goal(client, db):
    user = User(email="unknown-goal@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    try:
        response = client.post(
            "/api/learning/sessions",
            json={
                "goal_id": "00000000-0000-0000-0000-000000000000",
                "started_at": "2026-09-06T09:00:00Z",
                "duration_minutes": 30,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_goal_does_not_create_session(client, db):
    owner = User(email="session-owner-a@example.com")
    other = User(email="session-owner-b@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    goal = LearningService(db, owner.id).create_goal(LearningGoalCreate(title="Private"))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(other.id, other.email)
    try:
        response = client.post(
            "/api/learning/sessions",
            json={
                "goal_id": goal.id,
                "started_at": "2026-09-06T09:00:00Z",
                "duration_minutes": 30,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert LearningService(db, other.id).list_sessions() == []


def test_session_listing_is_owner_scoped_and_goal_filter_works(client, db):
    owner = User(email="list-owner@example.com")
    other = User(email="list-other@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    owner_service = LearningService(db, owner.id)
    other_service = LearningService(db, other.id)
    first_goal = owner_service.create_goal(LearningGoalCreate(title="First"))
    second_goal = owner_service.create_goal(LearningGoalCreate(title="Second"))
    owner_service.create_session(
        LearningSessionCreate(
            goal_id=first_goal.id,
            started_at=datetime(2026, 9, 6, 9, 0),
            duration_minutes=30,
        )
    )
    owner_service.create_session(
        LearningSessionCreate(
            goal_id=second_goal.id,
            started_at=datetime(2026, 9, 6, 10, 0),
            duration_minutes=45,
        )
    )
    other_goal = other_service.create_goal(LearningGoalCreate(title="Other"))
    other_service.create_session(
        LearningSessionCreate(
            goal_id=other_goal.id,
            started_at=datetime(2026, 9, 6, 11, 0),
            duration_minutes=60,
        )
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(owner.id, owner.email)
    try:
        all_response = client.get("/api/learning/sessions")
        filtered_response = client.get("/api/learning/sessions", params={"goal_id": first_goal.id})
        cross_user_filter = client.get("/api/learning/sessions", params={"goal_id": other_goal.id})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert all_response.status_code == 200
    assert len(all_response.json()) == 2
    assert filtered_response.status_code == 200
    assert len(filtered_response.json()) == 1
    assert filtered_response.json()[0]["goal_id"] == first_goal.id
    assert cross_user_filter.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"goal_id": "goal", "started_at": "2026-09-06T09:00:00Z", "duration_minutes": 0},
        {
            "goal_id": "goal",
            "started_at": "2026-09-06T09:00:00Z",
            "duration_minutes": 30,
            "user_id": "other-user",
        },
        {
            "goal_id": "goal",
            "started_at": "2026-09-06T09:00:00Z",
            "duration_minutes": 30,
            "unexpected": True,
        },
    ],
)
def test_session_create_rejects_invalid_or_unknown_fields(client, payload):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        "validation-user", "validation@example.com"
    )
    try:
        response = client.post("/api/learning/sessions", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422


def test_session_create_rejects_reversed_timestamps():
    with pytest.raises(ValueError, match="ended_at"):
        LearningSessionCreate(
            goal_id="goal",
            started_at=datetime(2026, 9, 6, 10, 0),
            ended_at=datetime(2026, 9, 6, 9, 0),
            duration_minutes=30,
        )


def test_session_updates_progress_and_recommendation(client, db):
    user = User(email="progress-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    service = LearningService(db, user.id)
    goal = service.create_goal(LearningGoalCreate(title="Progress"))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    try:
        response = client.post(
            "/api/learning/sessions",
            json={
                "goal_id": goal.id,
                "started_at": "2026-09-06T09:00:00Z",
                "duration_minutes": 50,
            },
        )
        app.dependency_overrides[get_learning_agent] = lambda: LearningAgent(
            service, MockProvider()
        )
        recommendation = client.post("/api/learning/agent/recommend", json={"goal_id": goal.id})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_learning_agent, None)

    assert response.status_code == 201
    assert recommendation.status_code == 200
    assert recommendation.json()["progress"]["total_sessions"] == 1
    assert recommendation.json()["progress"]["total_minutes"] == 50

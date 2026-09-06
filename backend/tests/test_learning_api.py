from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agents.learning.agent import LearningAgent
from app.api.dependencies import CurrentUser
from app.api.routes.learning import get_learning_agent, get_learning_service
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User
from app.providers.mock import MockProvider
from app.schemas.learning import LearningAgentResponse, LearningGoalCreate, LearningProgress
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

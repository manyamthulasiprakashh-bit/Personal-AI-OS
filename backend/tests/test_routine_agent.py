from datetime import date

from fastapi.testclient import TestClient

from app.agents.routine.agent import RoutineAgent
from app.api.routes.routine import get_routine_agent
from app.main import app
from app.providers.mock import MockProvider


class RecordingProvider:
    def __init__(self):
        self.progress = None
        self.target_date = None

    def generate_daily_review(self, progress, *, target_date):
        self.progress = progress
        self.target_date = target_date
        return {"summary": "mock review", "productivity_score": progress["productivity_score"]}


def test_mock_provider_returns_structured_review():
    progress = {
        "total_tasks": 3,
        "completed_tasks": 2,
        "completion_percentage": 66.7,
        "actual_minutes": 90,
        "productivity_score": 66,
    }

    review = MockProvider().generate_daily_review(progress, target_date=date(2026, 9, 6))

    assert set(review) == {
        "summary",
        "observations",
        "recommendations",
        "tomorrow_priorities",
    }
    assert isinstance(review["observations"], list)
    assert isinstance(review["recommendations"], list)
    assert isinstance(review["tomorrow_priorities"], list)


def test_review_day_uses_daily_progress_tool(monkeypatch):
    provider = RecordingProvider()
    expected_progress = {"completed_tasks": 1, "productivity_score": 100}
    calls = []

    def fake_progress(target_date):
        calls.append(target_date)
        return expected_progress

    monkeypatch.setattr(
        "app.agents.routine.agent.ALLOWED_TOOLS",
        {"get_daily_progress": fake_progress},
    )
    agent = RoutineAgent(provider=provider)

    result = agent.review_day(date(2026, 9, 6))

    assert calls == [date(2026, 9, 6)]
    assert provider.progress is expected_progress
    assert result["progress"] is expected_progress


def test_review_day_enforces_tool_allowlist():
    agent = RoutineAgent(provider=RecordingProvider())

    try:
        agent.execute("not_allowed", date.today())
    except ValueError as error:
        assert "not_allowed" in str(error)
    else:
        raise AssertionError("disallowed tool was executed")


def test_agent_review_endpoint_returns_progress_and_review():
    client = TestClient(app)
    provider = RecordingProvider()
    agent = RoutineAgent(provider=provider)
    app.dependency_overrides[get_routine_agent] = lambda: agent

    try:
        response = client.post("/api/routine/agent/review", json={"date": "2026-09-06"})
    finally:
        app.dependency_overrides.pop(get_routine_agent, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["progress"]["productivity_score"] == provider.progress["productivity_score"]
    assert body["review"]["summary"] == "mock review"


def test_agent_review_endpoint_uses_agent_review_day():
    client = TestClient(app)
    called = []

    class StubAgent:
        def review_day(self, target_date):
            called.append(target_date)
            return {
                "progress": {
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "pending_tasks": 0,
                    "skipped_tasks": 0,
                    "completion_percentage": 0.0,
                    "planned_minutes": 0,
                    "actual_minutes": 0,
                    "category_breakdown": {},
                    "habit_completion": {},
                    "productivity_score": 0,
                },
                "review": {"summary": "stub"},
            }

    app.dependency_overrides[get_routine_agent] = lambda: StubAgent()
    try:
        response = client.post("/api/routine/agent/review", json={"date": "2026-09-06"})
    finally:
        app.dependency_overrides.pop(get_routine_agent, None)

    assert response.status_code == 200
    assert called == [date(2026, 9, 6)]
    assert response.json()["review"]["summary"] == "stub"

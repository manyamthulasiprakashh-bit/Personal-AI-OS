from datetime import date

from fastapi.testclient import TestClient

from app.agents.routine.agent import RoutineAgent
from app.api.routes.routine import get_routine_agent
from app.main import app
from app.providers.mock import MockProvider


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


class _StubService:
    """Minimal stand-in for RoutineService in agent-only tests."""

    def __init__(self):
        self.user_id = TEST_USER_ID

    def calculate_daily_progress(self, target_date):
        return {
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
        }


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

    def fake_progress(service, target_date):
        calls.append(target_date)
        return expected_progress

    monkeypatch.setattr(
        "app.agents.routine.agent.ALLOWED_TOOLS",
        {"get_daily_progress": fake_progress},
    )
    agent = RoutineAgent(service=_StubService(), provider=provider)

    result = agent.review_day(date(2026, 9, 6))

    assert calls == [date(2026, 9, 6)]
    assert provider.progress is expected_progress
    assert result["progress"] is expected_progress


def test_review_day_enforces_tool_allowlist():
    agent = RoutineAgent(service=_StubService(), provider=RecordingProvider())

    try:
        agent.execute("not_allowed", date.today())
    except ValueError as error:
        assert "not_allowed" in str(error)
    else:
        raise AssertionError("disallowed tool was executed")


def test_agent_review_endpoint_returns_progress_and_review():
    client = TestClient(app)
    provider = RecordingProvider()
    agent = RoutineAgent(service=_StubService(), provider=provider)
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


# ---------- Phase 8C ownership tests ----------


def test_agent_review_sees_only_own_users_data():
    """RoutineAgent reviewing as User A must not see User B's tasks."""
    from app.database.session import SessionLocal
    from app.models.user import User
    from app.services.routine_service import RoutineService

    session = SessionLocal()
    try:
        user_a = User(email=f"agent-a-{date.today()}@example.com")
        user_b = User(email=f"agent-b-{date.today()}@example.com")
        session.add_all([user_a, user_b])
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)

        service_a = RoutineService(session, user_a.id)
        service_b = RoutineService(session, user_b.id)

        service_a.create_task({"title": "A's task", "planned_date": date.today()})
        service_b.create_task({"title": "B's task", "planned_date": date.today()})

        agent_a = RoutineAgent(service=service_a, provider=RecordingProvider())
        result_a = agent_a.review_day(date.today())

        # Agent A's progress reflects only A's task
        assert result_a["progress"]["total_tasks"] == 1

        # Agent B sees only B's task
        agent_b = RoutineAgent(service=service_b, provider=RecordingProvider())
        result_b = agent_b.review_day(date.today())
        assert result_b["progress"]["total_tasks"] == 1

        # Cleanup tasks so uniqueness constraint on (user_id, title, planned_date)
        # doesn't collide with other tests running on the same date.
        for task in service_a.repository.list_tasks():
            session.delete(task)
        for task in service_b.repository.list_tasks():
            session.delete(task)
        session.commit()
    finally:
        session.close()


def test_agent_cannot_mutate_other_users_task():
    """RoutineAgent scoped to User B gets 404 when trying to complete User A's task."""
    from fastapi import HTTPException
    from app.database.session import SessionLocal
    from app.models.user import User
    from app.services.routine_service import RoutineService

    session = SessionLocal()
    try:
        user_a = User(email=f"agent-mut-a-{date.today()}@example.com")
        user_b = User(email=f"agent-mut-b-{date.today()}@example.com")
        session.add_all([user_a, user_b])
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)

        service_a = RoutineService(session, user_a.id)
        task = service_a.create_task({"title": "A's protected task", "planned_date": date.today()})

        service_b = RoutineService(session, user_b.id)
        agent_b = RoutineAgent(service=service_b, provider=RecordingProvider())

        try:
            agent_b.execute("complete_task", task.id)
            raise AssertionError("agent B should not complete user A's task")
        except HTTPException as error:
            assert error.status_code == 404

        # Verify the task is still pending
        session.refresh(task)
        assert task.status == "pending"

        # Cleanup
        session.delete(task)
        session.commit()
    finally:
        session.close()

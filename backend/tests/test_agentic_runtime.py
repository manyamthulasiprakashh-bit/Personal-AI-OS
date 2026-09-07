from __future__ import annotations

from uuid import uuid4
from time import sleep

import pytest
from fastapi.testclient import TestClient

from app.agentic.planner import ScriptedPlanner
from app.agentic.state import PlanDecision
from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User
from app.providers.factory import get_job_provider
from app.providers.job import MockJobProvider
from app.schemas.job import JobOpportunityCreate
from app.services.agentic_service import AgenticRuntimeService
from app.services.job_service import JobService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_user(db, prefix: str = "agentic") -> User:
    user = User(email=f"{prefix}-{uuid4()}@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_scripted_planner_executes_observes_replans_and_completes(db):
    user = create_user(db)
    job = JobService(db, user.id).create(
        JobOpportunityCreate(title="AI Engineer", company="Example", description_snapshot="Python")
    )
    planner = ScriptedPlanner(
        [
            PlanDecision(decision="call_tool", tool="job.analyze", arguments={"job_id": job.id}),
            PlanDecision(decision="call_tool", tool="learning.recommend", arguments={}),
            PlanDecision(decision="complete", summary="Reviewed the role and current progress."),
        ]
    )
    service = AgenticRuntimeService(db, CurrentUser(user.id, user.email), planner=planner)

    result = service.create_and_run("Prepare me for this AI Engineer role")

    assert result.status == "completed"
    assert result.tool_call_count == 2
    assert result.planner_call_count == 3
    assert [step.capability for step in result.plan_steps] == ["job.analyze", "learning.recommend"]
    assert [step.sequence for step in result.plan_steps] == [1, 2]
    assert len(result.plan_steps[0].tool_calls[0].observation.content) > 0
    assert any(event.event_type == "observation_received" for event in result.events)
    assert any(event.event_type == "planner_completed" for event in result.events)
    assert [event.sequence for event in result.events] == list(range(1, len(result.events) + 1))


def test_invalid_tool_selection_fails_without_execution(db):
    user = create_user(db)
    planner = ScriptedPlanner(
        [PlanDecision(decision="call_tool", tool="database.query", arguments={})]
    )
    service = AgenticRuntimeService(db, CurrentUser(user.id, user.email), planner=planner)

    result = service.create_and_run("Inspect my data")

    assert result.status == "failed"
    assert result.failure_summary == "planner selected an unavailable capability"
    assert result.tool_call_count == 0


def test_repeated_identical_calls_are_bounded(db):
    user = create_user(db)
    planner = ScriptedPlanner(
        [
            PlanDecision(decision="call_tool", tool="learning.recommend", arguments={}),
            PlanDecision(decision="call_tool", tool="learning.recommend", arguments={}),
            PlanDecision(decision="call_tool", tool="learning.recommend", arguments={}),
        ]
    )
    service = AgenticRuntimeService(
        db,
        CurrentUser(user.id, user.email),
        planner=planner,
        max_repeated_identical_calls=2,
    )

    result = service.create_and_run("Review my learning progress")

    assert result.status == "failed"
    assert result.failure_summary == "repeated identical tool call limit exceeded"
    assert result.tool_call_count == 2


def test_tool_deadline_and_failed_observation_cannot_complete(db):
    user = create_user(db)

    class SlowExecutor:
        def catalogue(self, names):
            return []

        def execute(self, capability_name, arguments, context):
            sleep(0.01)
            return {"ok": True}

    planner = ScriptedPlanner(
        [
            PlanDecision(decision="call_tool", tool="learning.recommend", arguments={}),
            PlanDecision(decision="complete", summary="This must not complete."),
        ]
    )
    service = AgenticRuntimeService(
        db,
        CurrentUser(user.id, user.email),
        planner=planner,
        executor=SlowExecutor(),
        tool_timeout_seconds=0.001,
    )

    result = service.create_and_run("Review my learning progress")

    assert result.status == "failed"
    assert result.failure_summary == "completion requires a summary and an observation"


def test_waiting_run_can_be_cancelled(db):
    user = create_user(db)
    service = AgenticRuntimeService(
        db,
        CurrentUser(user.id, user.email),
        planner=ScriptedPlanner([PlanDecision(decision="ask_user", question="Need more detail")]),
    )

    waiting = service.create_and_run("Prepare me")
    cancelled = service.cancel(waiting.id)

    assert waiting.status == "waiting_for_user"
    assert cancelled.status == "cancelled"


def test_agent_run_api_is_owner_scoped(db):
    owner = create_user(db, "owner")
    other = create_user(db, "other")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(owner.id, owner.email)
    try:
        response = TestClient(app).post("/api/agent/runs", json={"goal": "Prepare me"})
        run_id = response.json()["id"]
        assert response.status_code == 201
        assert response.json()["status"] == "waiting_for_user"

        app.dependency_overrides[get_current_user] = lambda: CurrentUser(other.id, other.email)
        hidden = TestClient(app).get(f"/api/agent/runs/{run_id}")
        assert hidden.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_agent_api_uses_existing_job_provider(db):
    user = create_user(db, "job")
    job = JobService(db, user.id).create(
        JobOpportunityCreate(title="AI Engineer", company="Example")
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user.id, user.email)
    app.dependency_overrides[get_job_provider] = lambda: MockJobProvider()
    try:
        response = TestClient(app).post(
            "/api/agent/runs",
            json={"goal": f"Help me prepare for job {job.id}"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_job_provider, None)

    assert response.status_code == 201, response.text
    assert response.json()["status"] in {"completed", "waiting_for_user", "failed"}
    assert response.json()["tool_call_count"] >= 1

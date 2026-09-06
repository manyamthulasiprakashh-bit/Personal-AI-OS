import pytest

from app.agents.learning.agent import LearningAgent, LearningProviderError
from app.providers.mock import MockProvider
from app.schemas.learning import LearningProgress, LearningRecommendation


class StubService:
    def __init__(self, progress: LearningProgress):
        self.progress = progress
        self.goal_ids = []

    def get_progress(self, goal_id=None):
        self.goal_ids.append(goal_id)
        return self.progress.model_copy(update={"goal_id": goal_id})


class RecordingProvider:
    def __init__(self):
        self.progress = None

    def generate_learning_recommendation(self, progress):
        self.progress = progress
        return LearningRecommendation(
            summary="Keep going",
            observations=["Progress is recorded."],
            recommendations=["Continue studying."],
            next_steps=["Record the next session."],
        )


def learning_progress():
    return LearningProgress(
        total_goals=1,
        active_goals=1,
        completed_goals=0,
        total_sessions=2,
        total_minutes=90,
    )


def test_agent_calls_progress_tool_and_passes_exact_progress_to_provider():
    service = StubService(learning_progress())
    provider = RecordingProvider()
    agent = LearningAgent(service, provider)

    result = agent.recommend("goal-1")

    assert service.goal_ids == ["goal-1"]
    assert provider.progress is result.progress
    assert isinstance(result.recommendation, LearningRecommendation)


def test_agent_allowlist_rejects_unknown_tools():
    agent = LearningAgent(StubService(learning_progress()), RecordingProvider())

    with pytest.raises(ValueError, match="not allowed"):
        agent.execute("create_learning_goal")


def test_agent_does_not_need_database_access():
    service = StubService(learning_progress())
    agent = LearningAgent(service, RecordingProvider())

    result = agent.recommend()

    assert result.progress.total_minutes == 90


def test_malformed_provider_output_fails_validation():
    class MalformedProvider:
        def generate_learning_recommendation(self, progress):
            return {"summary": "missing required fields"}

    agent = LearningAgent(StubService(learning_progress()), MalformedProvider())

    with pytest.raises(LearningProviderError):
        agent.recommend()


def test_provider_failure_is_wrapped():
    class FailingProvider:
        def generate_learning_recommendation(self, progress):
            raise RuntimeError("provider unavailable")

    agent = LearningAgent(StubService(learning_progress()), FailingProvider())

    with pytest.raises(LearningProviderError):
        agent.recommend()


def test_mock_provider_returns_structured_empty_recommendation():
    recommendation = MockProvider().generate_learning_recommendation(
        LearningProgress(
            total_goals=0,
            active_goals=0,
            completed_goals=0,
            total_sessions=0,
            total_minutes=0,
        )
    )

    assert recommendation.summary == "No learning goals have been created yet."
    assert recommendation.observations
    assert recommendation.recommendations
    assert recommendation.next_steps


def test_mock_provider_returns_structured_active_goal_recommendation():
    recommendation = MockProvider().generate_learning_recommendation(learning_progress())

    assert recommendation.summary == "You have 1 learning goals in progress."
    assert recommendation.observations
    assert recommendation.recommendations
    assert recommendation.next_steps

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agentic.planner import LLMPlannerProvider, LLMPlannerProviderError
from app.agentic.state import PlanDecision, PlannerState
from app.config import Settings


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def response_for(parsed):
    return SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=[],
        output_parsed=parsed,
    )


def wire_response_for(**values):
    return response_for(values)


def planner(fake_response):
    settings = Settings(
        openai_api_key="test-key",
        agent_planner_model="test-model",
        agent_planner_timeout_seconds=4,
        agent_planner_max_output_tokens=128,
    )
    responses = FakeResponses(fake_response)
    client = SimpleNamespace(responses=responses)
    return LLMPlannerProvider(settings=settings, client=client), responses


def tools():
    return [
        {
            "name": "job.analyze",
            "description": "Analyze one owned job.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "risk_level": "low",
            "requires_approval": False,
        }
    ]


def test_llm_planner_returns_structured_decision_and_bounded_context():
    provider, responses = planner(
        response_for(
            PlanDecision(decision="call_tool", tool="job.analyze", arguments={"job_id": "job-1"})
        )
    )

    result = provider.decide(
        "Prepare me for this role",
        PlannerState(
            goal="Prepare me for this role",
            iteration=1,
            observations=[{"tool": "job.analyze", "result": {"text": "untrusted data"}}],
        ),
        tools(),
    )

    assert result.decision == "call_tool"
    request = responses.calls[0]
    assert request["model"] == "test-model"
    assert request["tools"] == []
    assert request["tool_choice"] == "none"
    assert "You do not execute or authorize actions" in request["input"][0]["content"]
    assert "untrusted data" in request["input"][1]["content"]
    assert "test-key" not in str(request)


def test_llm_planner_rejects_unknown_tool():
    provider, _ = planner(
        response_for(PlanDecision(decision="call_tool", tool="admin.delete", arguments={}))
    )

    with pytest.raises(LLMPlannerProviderError, match="unavailable capability"):
        provider.decide("Delete something", PlannerState(goal="Delete something"), tools())


def test_llm_planner_converts_strict_wire_arguments_to_runtime_decision():
    provider, _ = planner(
        wire_response_for(
            decision="call_tool",
            tool="job.analyze",
            arguments_json='{"job_id":"job-1"}',
            summary=None,
            question=None,
        )
    )

    result = provider.decide("Analyze", PlannerState(goal="Analyze"), tools())

    assert result.arguments == {"job_id": "job-1"}


def test_llm_planner_rejects_malformed_structured_output():
    provider, _ = planner(response_for({"decision": "not-a-decision", "tool": "job.analyze"}))

    with pytest.raises(LLMPlannerProviderError):
        provider.decide("Analyze", PlannerState(goal="Analyze"), tools())


def test_llm_planner_converts_provider_failure_to_safe_error():
    settings = Settings(openai_api_key="test-key", agent_planner_model="test-model")

    class FailingResponses:
        def parse(self, **kwargs):
            raise RuntimeError("provider secret")

    provider = LLMPlannerProvider(
        settings=settings, client=SimpleNamespace(responses=FailingResponses())
    )

    with pytest.raises(LLMPlannerProviderError) as error:
        provider.decide("Analyze", PlannerState(goal="Analyze"), tools())
    assert str(error.value) == ""

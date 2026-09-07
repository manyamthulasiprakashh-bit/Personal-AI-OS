from __future__ import annotations

import json
import httpx
import pytest

from app.agentic.planner import LLMPlannerProviderError
from app.agentic.state import PlannerState
from app.config import Settings
from app.providers.local_planner import LocalLLMPlannerProvider


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.request = None

    def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


def response(content, status_code=200):
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    return httpx.Response(
        status_code,
        request=request,
        json={"message": {"content": content}},
    )


def provider(content):
    client = FakeClient(response(content))
    settings = Settings(
        agent_planner_provider="local",
        agent_planner_model="local-model",
        agent_planner_local_base_url="http://localhost:11434",
    )
    return LocalLLMPlannerProvider(settings=settings, client=client), client


def valid_wire(**overrides):
    values = {
        "decision": "call_tool",
        "tool": "job.analyze",
        "arguments_json": '{"job_id":"job-1"}',
        "summary": None,
        "question": None,
    }
    values.update(overrides)
    return json.dumps(values)


def tools():
    return [{"name": "job.analyze", "description": "analyze", "input_schema": {}}]


def test_local_planner_returns_validated_decision_and_safe_request():
    planner, client = provider(valid_wire())

    decision = planner.decide("Prepare me", PlannerState(goal="Prepare me"), tools())

    assert decision.tool == "job.analyze"
    assert decision.arguments == {"job_id": "job-1"}
    url, kwargs = client.request
    assert url == "http://localhost:11434/api/chat"
    assert kwargs["json"]["format"]["additionalProperties"] is False
    assert kwargs["json"]["stream"] is False
    assert "local-model" in kwargs["json"]["model"]
    assert "Prepare me" in kwargs["json"]["messages"][1]["content"]


def test_local_planner_rejects_unknown_capability():
    planner, _ = provider(valid_wire(tool="admin.delete"))

    with pytest.raises(LLMPlannerProviderError, match="unavailable capability"):
        planner.decide("Delete", PlannerState(goal="Delete"), tools())


def test_local_planner_rejects_malformed_output():
    planner, _ = provider("not-json")

    with pytest.raises(LLMPlannerProviderError, match="invalid structured output"):
        planner.decide("Prepare", PlannerState(goal="Prepare"), tools())


def test_local_planner_converts_http_failure_to_safe_error():
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    failing = httpx.Response(500, request=request)
    client = FakeClient(failing)
    planner = LocalLLMPlannerProvider(Settings(agent_planner_model="local-model"), client=client)

    with pytest.raises(LLMPlannerProviderError, match="request failed"):
        planner.decide("Prepare", PlannerState(goal="Prepare"), tools())


def test_local_planner_rejects_non_loopback_url():
    with pytest.raises(LLMPlannerProviderError, match="loopback"):
        LocalLLMPlannerProvider(
            Settings(
                agent_planner_model="local-model",
                agent_planner_local_base_url="https://example.invalid",
            )
        )

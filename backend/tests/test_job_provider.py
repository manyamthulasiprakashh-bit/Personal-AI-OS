from types import SimpleNamespace

import pytest

from app.config import Settings
from app.providers import factory
from app.providers.job import (
    LLMJobProvider,
    LLMJobProviderError,
    MockJobProvider,
)
from app.schemas.job import JobAnalysis, JobAnalysisInput


def job_input(**updates):
    payload = {
        "job_id": "job-1",
        "title": "Backend Engineer",
        "company": "Example Inc",
        "location": "Remote",
        "work_mode": "remote",
        "source": "manual",
        "description_snapshot": "Build APIs",
        "notes": "Review later",
        "status": "saved",
    }
    payload.update(updates)
    return JobAnalysisInput(**payload)


def valid_analysis():
    return JobAnalysis(
        summary="A backend opportunity.",
        extracted_requirements=["API development"],
        positive_signals=["Remote work"],
        unknowns=["Compensation"],
        suggested_next_steps=["Review the role"],
        confidence="medium",
    )


class FakeResponses:
    def __init__(
        self, parsed=None, error=None, status="completed", incomplete_details=None, output=None
    ):
        self.parsed = parsed
        self.error = error
        self.status = status
        self.incomplete_details = incomplete_details
        self.output = output or []
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            output_parsed=self.parsed,
            status=self.status,
            incomplete_details=self.incomplete_details,
            output=self.output,
        )


class FakeClient:
    def __init__(
        self, parsed=None, error=None, status="completed", incomplete_details=None, output=None
    ):
        self.responses = FakeResponses(
            parsed=parsed,
            error=error,
            status=status,
            incomplete_details=incomplete_details,
            output=output,
        )


def llm_provider(client=None, **settings):
    return LLMJobProvider(
        Settings(
            job_provider="llm",
            openai_api_key="test-key",
            openai_model="test-model",
            **settings,
        ),
        client=client,
    )


def test_llm_provider_returns_typed_structured_output_and_disables_tools():
    client = FakeClient(parsed=valid_analysis())
    result = llm_provider(client).generate_job_analysis(job_input())

    assert result == valid_analysis()
    call = client.responses.calls[0]
    assert call["text_format"] is JobAnalysis
    assert call["store"] is False
    assert call["tools"] == []
    assert call["tool_choice"] == "none"
    assert call["model"] == "test-model"
    assert "UNTRUSTED JOB DATA" in call["input"][1]["content"]
    assert "Ignore" not in call["input"][0]["content"]


def test_llm_provider_rejects_incomplete_response():
    with pytest.raises(LLMJobProviderError):
        llm_provider(
            FakeClient(parsed=valid_analysis(), status="incomplete")
        ).generate_job_analysis(job_input())


def test_llm_provider_rejects_incomplete_details_on_completed_response():
    with pytest.raises(LLMJobProviderError):
        llm_provider(
            FakeClient(
                parsed=valid_analysis(),
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            )
        ).generate_job_analysis(job_input())


def test_llm_provider_rejects_refusal_response():
    refusal = SimpleNamespace(
        type="message",
        content=[SimpleNamespace(type="refusal", refusal="sensitive details")],
    )

    with pytest.raises(LLMJobProviderError):
        llm_provider(FakeClient(parsed=valid_analysis(), output=[refusal])).generate_job_analysis(
            job_input()
        )


@pytest.mark.parametrize(
    "parsed",
    [None, {"summary": "missing"}, {"summary": "x", "unexpected": True}],
)
def test_llm_provider_rejects_malformed_structured_output(parsed):
    with pytest.raises(LLMJobProviderError):
        llm_provider(FakeClient(parsed=parsed)).generate_job_analysis(job_input())


def test_llm_provider_rejects_invalid_confidence():
    parsed = valid_analysis().model_dump()
    parsed["confidence"] = "certain"

    with pytest.raises(LLMJobProviderError):
        llm_provider(FakeClient(parsed=parsed)).generate_job_analysis(job_input())


def test_llm_provider_requires_key_and_model_without_client():
    with pytest.raises(LLMJobProviderError):
        LLMJobProvider(Settings(job_provider="llm")).generate_job_analysis(job_input())

    with pytest.raises(LLMJobProviderError):
        LLMJobProvider(
            Settings(job_provider="llm", openai_api_key="test-key")
        ).generate_job_analysis(job_input())


@pytest.mark.parametrize(
    "job, expected",
    [
        (job_input(description_snapshot="x" * 16001), "too large"),
        (job_input(notes="x" * 4001), "too large"),
        (job_input(description_snapshot="x" * 15000, notes="y" * 5000), "too large"),
    ],
)
def test_llm_provider_rejects_oversized_input(job, expected):
    with pytest.raises(LLMJobProviderError, match=expected):
        llm_provider(FakeClient(parsed=valid_analysis())).generate_job_analysis(job)


@pytest.mark.parametrize(
    "error",
    [TimeoutError(), ConnectionError(), PermissionError(), RuntimeError("rate limit")],
)
def test_llm_provider_wraps_provider_failures(error):
    with pytest.raises(LLMJobProviderError):
        llm_provider(FakeClient(error=error)).generate_job_analysis(job_input())


def test_factory_defaults_to_mock_and_allows_explicit_llm(monkeypatch):
    mock_settings = Settings(job_provider="mock")
    llm_settings = Settings(
        job_provider="llm", openai_api_key="test-key", openai_model="test-model"
    )
    monkeypatch.setattr(factory, "get_settings", lambda: mock_settings)
    assert isinstance(factory.get_job_provider(), MockJobProvider)

    monkeypatch.setattr(factory, "get_settings", lambda: llm_settings)
    assert isinstance(factory.get_job_provider(), LLMJobProvider)


def test_factory_invalid_provider_is_safe(monkeypatch):
    monkeypatch.setattr(factory, "get_settings", lambda: Settings(job_provider="other"))

    provider = factory.get_job_provider()

    with pytest.raises(LLMJobProviderError):
        provider.generate_job_analysis(job_input())

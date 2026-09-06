from __future__ import annotations

from typing import Any

from app.agents.job.tools import ALLOWED_TOOLS
from app.providers.job import JobProvider
from app.schemas.job import JobAnalysis, JobAnalysisResponse, JobOpportunityResponse
from app.services.job_service import JobService


class JobProviderError(RuntimeError):
    """Raised when a job provider cannot return valid analysis."""


class JobAnalysisAgent:
    def __init__(self, service: JobService, provider: JobProvider):
        self.service = service
        self.provider = provider
        self.allowed_tools = set(ALLOWED_TOOLS)

    def execute(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        if tool_name not in self.allowed_tools:
            raise ValueError(f"Tool '{tool_name}' is not allowed")
        return ALLOWED_TOOLS[tool_name](self.service, *args, **kwargs)

    def analyze(self, job_id: str) -> JobAnalysisResponse:
        job_input = self.execute("get_job_analysis_input", job_id)
        try:
            analysis = JobAnalysis.model_validate(self.provider.generate_job_analysis(job_input))
        except Exception as error:
            raise JobProviderError from error
        job = self.service.get(job_id)
        return JobAnalysisResponse(
            job=JobOpportunityResponse.model_validate(job), analysis=analysis
        )

from __future__ import annotations

from collections.abc import Callable

from app.schemas.job import JobAnalysisInput
from app.services.job_service import JobService


def get_job_analysis_input(service: JobService, job_id: str) -> JobAnalysisInput:
    return service.get_analysis_input(job_id)


ALLOWED_TOOLS: dict[str, Callable[..., JobAnalysisInput]] = {
    "get_job_analysis_input": get_job_analysis_input,
}

from __future__ import annotations

from typing import Protocol

from app.schemas.job import JobAnalysis, JobAnalysisInput


class JobProvider(Protocol):
    def generate_job_analysis(self, job: JobAnalysisInput) -> JobAnalysis: ...


class MockJobProvider:
    def generate_job_analysis(self, job: JobAnalysisInput) -> JobAnalysis:
        has_description = bool(job.description_snapshot and job.description_snapshot.strip())
        requirements = ["Review the user-provided job description for role requirements."]
        unknowns = [] if has_description else ["No job description snapshot was provided."]
        positive_signals = [f"The opportunity is saved for review at {job.company}."]
        next_steps = ["Review the saved opportunity and decide whether to pursue it."]
        summary = f"{job.title} at {job.company} is available for manual review."
        return JobAnalysis(
            summary=summary,
            extracted_requirements=requirements,
            positive_signals=positive_signals,
            unknowns=unknowns,
            suggested_next_steps=next_steps,
            confidence="low" if not has_description else "medium",
        )

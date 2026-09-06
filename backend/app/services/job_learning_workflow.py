from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.agents.job.agent import JobAnalysisAgent
from app.api.dependencies import CurrentUser
from app.capabilities.job_learning import (
    build_job_learning_context,
    recommend_job_learning,
)
from app.providers.factory import get_job_provider
from app.providers.job import JobProvider
from app.schemas.job import (
    JobAnalysis,
    JobLearningContext,
    JobLearningRecommendation,
)
from app.services.job_service import JobService


class JobLearningWorkflowService:
    """Run the fixed, synchronous Job Analysis -> Learning composition."""

    max_workflow_depth = 1
    max_delegated_capability_calls = 1

    def __init__(
        self,
        db: Session,
        current_user: CurrentUser,
        job_provider: JobProvider | None = None,
        analysis_agent: JobAnalysisAgent | None = None,
        context_builder: Callable[[str, JobAnalysis], JobLearningContext] = build_job_learning_context,
        recommendation_builder: Callable[
            [JobLearningContext], JobLearningRecommendation
        ] = recommend_job_learning,
    ):
        self.current_user = current_user
        self.analysis_agent = analysis_agent or JobAnalysisAgent(
            JobService(db, current_user.id), job_provider or get_job_provider()
        )
        self.context_builder = context_builder
        self.recommendation_builder = recommendation_builder

    def run(self, job_id: str) -> JobLearningRecommendation:
        analysis_response = self.analysis_agent.analyze(job_id)
        context = self.context_builder(job_id, analysis_response.analysis)
        return self.recommendation_builder(context)
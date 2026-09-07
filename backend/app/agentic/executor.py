from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agentic.context import AgentExecutionContext
from app.agentic.policies import AgenticExecutionPolicy
from app.api.dependencies import CurrentUser
from app.agents.job.agent import JobAnalysisAgent
from app.agents.learning.agent import LearningAgent
from app.orchestration.registry import CapabilityDefinition, CapabilityRegistry
from app.providers.factory import get_job_provider, get_learning_provider, get_stock_provider
from app.providers.job import JobProvider
from app.providers.learning import LearningProvider
from app.providers.stock import StockProvider
from app.schemas.orchestrator import JobAnalyzeInput, LearningRecommendInput, StockQuoteInput
from app.services.job_learning_workflow import JobLearningWorkflowService
from app.services.job_service import JobService
from app.services.learning_service import LearningService
from app.services.stock_service import StockService


class DirectCapabilityExecutor:
    def __init__(
        self,
        db: Session,
        current_user: CurrentUser,
        learning_provider: LearningProvider | None = None,
        job_provider: JobProvider | None = None,
        stock_provider: StockProvider | None = None,
        policy: AgenticExecutionPolicy | None = None,
    ):
        self.db = db
        self.current_user = current_user
        self.learning_provider = learning_provider or get_learning_provider()
        self.job_provider = job_provider or get_job_provider()
        self.stock_provider = stock_provider or get_stock_provider()
        self.policy = policy or AgenticExecutionPolicy()

    def catalogue(self, names: set[str]) -> list[dict[str, object]]:
        return [self._catalogue_entry(CapabilityRegistry.get(name)) for name in sorted(names)]

    def _catalogue_entry(self, capability: CapabilityDefinition) -> dict[str, object]:
        return {
            "name": capability.name,
            "description": capability.description,
            "input_schema": capability.input_model.model_json_schema(),
            "output_schema": capability.output_model.model_json_schema(),
            "risk_level": capability.risk_level,
            "requires_approval": self.policy.requires_approval(capability),
        }

    def execute(
        self, capability_name: str, arguments: dict[str, Any], context: AgentExecutionContext
    ) -> BaseModel:
        capability = CapabilityRegistry.get(capability_name)
        self.policy.authorize(capability)
        payload = capability.input_model.model_validate(arguments)
        if capability_name == "job.analyze":
            typed = JobAnalyzeInput.model_validate(payload)
            return JobAnalysisAgent(
                JobService(self.db, context.user_id), self.job_provider
            ).analyze(typed.job_id)
        if capability_name == "learning.recommend":
            typed = LearningRecommendInput.model_validate(payload)
            return LearningAgent(
                LearningService(self.db, context.user_id), self.learning_provider
            ).recommend(typed.goal_id)
        if capability_name == "job.learning":
            typed = JobAnalyzeInput.model_validate(payload)
            return JobLearningWorkflowService(
                self.db, context.current_user, job_provider=self.job_provider
            ).run(typed.job_id)
        if capability_name == "stock.quote":
            typed = StockQuoteInput.model_validate(payload)
            return StockService(self.stock_provider).get_quote(typed.symbol)
        raise KeyError("unsupported capability")

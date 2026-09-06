from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.job.agent import JobAnalysisAgent
from app.agents.learning.agent import LearningAgent
from app.api.dependencies import CurrentUser
from app.orchestration.policy import ReadOnlyExecutionPolicy
from app.orchestration.registry import CapabilityDefinition, CapabilityRegistry
from app.providers.factory import get_job_provider, get_learning_provider, get_stock_provider
from app.providers.job import JobProvider
from app.providers.learning import LearningProvider
from app.providers.stock import StockProvider
from app.schemas.job import JobAnalysisResponse
from app.schemas.learning import LearningAgentResponse
from app.schemas.orchestrator import (
    JobAnalyzeInput,
    LearningRecommendInput,
    OrchestratorResponse,
    StockQuoteInput,
)
from app.schemas.stock import StockQuote
from app.services.job_service import JobService
from app.services.learning_service import LearningService
from app.services.stock_service import StockService


class OrchestratorError(ValueError):
    """Base class for safe request classification failures."""


class UnknownIntentError(OrchestratorError):
    pass


class AmbiguousIntentError(OrchestratorError):
    pass


class MissingCapabilityArgumentError(OrchestratorError):
    pass


class UnsupportedCapabilityError(OrchestratorError):
    pass


@dataclass(frozen=True)
class ClassifiedRequest:
    capability: CapabilityDefinition
    arguments: BaseModel


class OrchestratorService:
    _job_id_pattern = re.compile(
        r"\bjob(?:\s+id)?\s*[:#]?\s*([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\b", re.I
    )
    _goal_id_pattern = re.compile(r"\bgoal(?:\s+id)?\s*[:#]?\s*([0-9a-f-]{8,100})\b", re.I)
    _stock_patterns = (
        re.compile(r"\b(?:price|quote)\s+(?:of|for)\s+([a-z][a-z0-9.-]{0,19})\b", re.I),
        re.compile(r"\b(?:stock|quote)\s+([a-z][a-z0-9.-]{0,19})\b", re.I),
        re.compile(r"^\s*([a-z][a-z0-9.-]{0,19})\s+quote\b", re.I),
    )

    def __init__(
        self,
        db: Session,
        current_user: CurrentUser,
        learning_provider: LearningProvider | None = None,
        job_provider: JobProvider | None = None,
        stock_provider: StockProvider | None = None,
    ):
        self.db = db
        self.current_user = current_user
        self.learning_provider = learning_provider or get_learning_provider()
        self.job_provider = job_provider or get_job_provider()
        self.stock_provider = stock_provider or get_stock_provider()
        self.policy = ReadOnlyExecutionPolicy()

    def classify(self, message: str) -> ClassifiedRequest:
        normalized = message.strip()
        lowered = normalized.lower()
        if not normalized:
            raise UnknownIntentError("unsupported request")

        if self._contains_denied_action(lowered):
            raise UnsupportedCapabilityError("unsupported capability")
        if self._is_multiple_request(lowered):
            raise AmbiguousIntentError("request must contain one capability")

        matches = []
        if self._is_learning(lowered):
            matches.append("learning.recommend")
        if self._is_job(lowered):
            matches.append("job.analyze")
        if self._is_stock(lowered):
            matches.append("stock.quote")
        if len(matches) == 0:
            raise UnknownIntentError("unsupported request")
        if len(matches) > 1:
            raise AmbiguousIntentError("request must contain one capability")

        capability = CapabilityRegistry.get(matches[0])
        if matches[0] == "learning.recommend":
            goal_match = self._goal_id_pattern.search(normalized)
            return ClassifiedRequest(
                capability=capability,
                arguments=LearningRecommendInput(
                    goal_id=goal_match.group(1) if goal_match else None
                ),
            )
        if matches[0] == "job.analyze":
            job_match = self._job_id_pattern.search(normalized)
            if job_match is None:
                raise MissingCapabilityArgumentError("job id is required")
            return ClassifiedRequest(
                capability=capability,
                arguments=JobAnalyzeInput(job_id=job_match.group(1)),
            )

        for pattern in self._stock_patterns:
            stock_match = pattern.search(normalized)
            if stock_match:
                return ClassifiedRequest(
                    capability=capability,
                    arguments=StockQuoteInput(symbol=stock_match.group(1)),
                )
        raise MissingCapabilityArgumentError("stock symbol is required")

    def run(self, message: str) -> OrchestratorResponse:
        classified = self.classify(message)
        self.policy.authorize(classified.capability)
        result = self._execute(classified)
        validated = classified.capability.output_model.model_validate(result)
        return OrchestratorResponse(capability=classified.capability.name, result=validated)

    def _execute(self, classified: ClassifiedRequest) -> BaseModel:
        handlers = {
            "learning_recommend": self._handle_learning_recommend,
            "job_analyze": self._handle_job_analyze,
            "stock_quote": self._handle_stock_quote,
        }
        handler = handlers.get(classified.capability.handler_name)
        if handler is None:
            raise UnsupportedCapabilityError("unsupported capability")
        return handler(classified.arguments)

    def _handle_learning_recommend(self, arguments: BaseModel) -> LearningAgentResponse:
        payload = LearningRecommendInput.model_validate(arguments)
        agent = LearningAgent(
            LearningService(self.db, self.current_user.id), self.learning_provider
        )
        return agent.recommend(payload.goal_id)

    def _handle_job_analyze(self, arguments: BaseModel) -> JobAnalysisResponse:
        payload = JobAnalyzeInput.model_validate(arguments)
        agent = JobAnalysisAgent(JobService(self.db, self.current_user.id), self.job_provider)
        return agent.analyze(payload.job_id)

    def _handle_stock_quote(self, arguments: BaseModel) -> StockQuote:
        payload = StockQuoteInput.model_validate(arguments)
        return StockService(self.stock_provider).get_quote(payload.symbol)

    @staticmethod
    def _is_learning(message: str) -> bool:
        return any(term in message for term in ("study", "learn", "learning")) or (
            "recommend" in message and "job" not in message
        )

    @staticmethod
    def _is_job(message: str) -> bool:
        return "job" in message and any(term in message for term in ("analy", "requirement"))

    @staticmethod
    def _is_stock(message: str) -> bool:
        return any(
            term in message
            for term in (
                "stock",
                "quote",
                "share price",
                "stock price",
                "current price",
                "price of",
            )
        )

    def _is_multiple_request(self, message: str) -> bool:
        if re.search(r"\b(?:and then|then)\b", message):
            return True
        stock_symbols = {
            match.group(1).upper()
            for pattern in self._stock_patterns
            for match in pattern.finditer(message)
        }
        return len(stock_symbols) > 1

    @staticmethod
    def _contains_denied_action(message: str) -> bool:
        return any(
            term in message
            for term in (
                "application",
                "trade",
                "trading",
                "brokerage",
                "buy",
                "sell",
                "execute_sql",
                "filesystem",
                "file system",
                "fetch url",
                "call tool",
            )
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Type

from pydantic import BaseModel

from app.schemas.job import JobAnalysisResponse
from app.schemas.learning import LearningAgentResponse
from app.schemas.orchestrator import JobAnalyzeInput, LearningRecommendInput, StockQuoteInput
from app.schemas.stock import StockQuote

RiskLevel = Literal["low"]
AccessMode = Literal["read_only"]
OwnershipMode = Literal["current_user", "global"]


@dataclass(frozen=True)
class CapabilityDefinition:
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    handler_name: str
    risk_level: RiskLevel
    access_mode: AccessMode
    ownership_mode: OwnershipMode


CAPABILITIES: dict[str, CapabilityDefinition] = {
    "learning.recommend": CapabilityDefinition(
        name="learning.recommend",
        description="Return a read-only learning recommendation.",
        input_model=LearningRecommendInput,
        output_model=LearningAgentResponse,
        handler_name="learning_recommend",
        risk_level="low",
        access_mode="read_only",
        ownership_mode="current_user",
    ),
    "job.analyze": CapabilityDefinition(
        name="job.analyze",
        description="Analyze one owned job opportunity without changing it.",
        input_model=JobAnalyzeInput,
        output_model=JobAnalysisResponse,
        handler_name="job_analyze",
        risk_level="low",
        access_mode="read_only",
        ownership_mode="current_user",
    ),
    "stock.quote": CapabilityDefinition(
        name="stock.quote",
        description="Return an informational stock quote.",
        input_model=StockQuoteInput,
        output_model=StockQuote,
        handler_name="stock_quote",
        risk_level="low",
        access_mode="read_only",
        ownership_mode="global",
    ),
}


class CapabilityRegistry:
    @staticmethod
    def get(name: str) -> CapabilityDefinition:
        capability = CAPABILITIES.get(name)
        if capability is None:
            raise KeyError("unsupported capability")
        return capability

    @staticmethod
    def names() -> frozenset[str]:
        return frozenset(CAPABILITIES)

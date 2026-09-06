from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobAnalysisResponse
from app.schemas.learning import LearningAgentResponse
from app.schemas.stock import StockQuote


class OrchestratorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=2000)


class LearningRecommendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str | None = None


class JobAnalyzeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., min_length=1, max_length=100)


class StockQuoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=1, max_length=20)


OrchestratorResult = Annotated[
    LearningAgentResponse | JobAnalysisResponse | StockQuote,
    Field(discriminator=None),
]


class OrchestratorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: Literal["learning.recommend", "job.analyze", "stock.quote"]
    result: OrchestratorResult

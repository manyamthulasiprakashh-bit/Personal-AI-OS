from __future__ import annotations

from typing import Any

from app.agents.learning.tools import ALLOWED_TOOLS
from app.providers.learning import LearningProvider
from app.schemas.learning import LearningAgentResponse, LearningRecommendation
from app.services.learning_service import LearningService


class LearningProviderError(RuntimeError):
    """Raised when the learning provider cannot return a valid recommendation."""


class LearningAgent:
    def __init__(self, service: LearningService, provider: LearningProvider):
        self.service = service
        self.provider = provider
        self.allowed_tools = set(ALLOWED_TOOLS)

    def execute(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        if tool_name not in self.allowed_tools:
            raise ValueError(f"Tool '{tool_name}' is not allowed")
        return ALLOWED_TOOLS[tool_name](self.service, *args, **kwargs)

    def recommend(self, goal_id: str | None = None) -> LearningAgentResponse:
        progress = self.execute("get_learning_progress", goal_id=goal_id)
        try:
            recommendation = LearningRecommendation.model_validate(
                self.provider.generate_learning_recommendation(progress)
            )
        except Exception as error:
            raise LearningProviderError from error
        return LearningAgentResponse(progress=progress, recommendation=recommendation)

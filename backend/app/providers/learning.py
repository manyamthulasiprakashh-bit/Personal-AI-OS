from __future__ import annotations

from typing import Protocol

from app.schemas.learning import LearningProgress, LearningRecommendation


class LearningProvider(Protocol):
    def generate_learning_recommendation(
        self, progress: LearningProgress
    ) -> LearningRecommendation: ...

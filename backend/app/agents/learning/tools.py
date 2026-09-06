from __future__ import annotations

from collections.abc import Callable

from app.schemas.learning import LearningProgress
from app.services.learning_service import LearningService


def get_learning_progress(service: LearningService, goal_id: str | None = None) -> LearningProgress:
    return service.get_progress(goal_id)


ALLOWED_TOOLS: dict[str, Callable[..., LearningProgress]] = {
    "get_learning_progress": get_learning_progress,
}

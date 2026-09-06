from __future__ import annotations

from datetime import date
from typing import Any

from app.providers.base import BaseProvider
from app.schemas.learning import LearningProgress, LearningRecommendation


class MockProvider(BaseProvider):
    def generate_daily_review(
        self, progress: dict[str, Any], *, target_date: date
    ) -> dict[str, Any]:
        return {
            "summary": (
                f"{progress['completed_tasks']} of {progress['total_tasks']} tasks completed. "
                f"Completion rate was {progress['completion_percentage']}%."
            ),
            "observations": [f"Actual work time was {progress['actual_minutes']} minutes."],
            "recommendations": [
                "Review remaining work and schedule the next highest-priority task first."
            ],
            "tomorrow_priorities": ["Plan the next highest-priority task before starting the day."],
        }

    def generate_learning_recommendation(
        self, progress: LearningProgress
    ) -> LearningRecommendation:
        if progress.total_goals == 0:
            return LearningRecommendation(
                summary="No learning goals have been created yet.",
                observations=["There is no stored learning activity to review."],
                recommendations=["Create a learning goal to begin tracking progress."],
                next_steps=["Define one focused learning goal and its target outcome."],
            )

        if progress.goal_id is not None:
            summary = f"This goal has {progress.total_sessions} recorded learning sessions."
        else:
            summary = f"You have {progress.total_goals} learning goals in progress."

        return LearningRecommendation(
            summary=summary,
            observations=[
                f"You have completed {progress.total_minutes} minutes across "
                f"{progress.total_sessions} learning sessions."
            ],
            recommendations=["Continue with a focused session on an active learning goal."],
            next_steps=["Record the next learning session after completing it."],
        )

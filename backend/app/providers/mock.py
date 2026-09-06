from __future__ import annotations

from datetime import date
from typing import Any

from app.providers.base import BaseProvider


class MockProvider(BaseProvider):
    def generate_daily_review(
        self, progress: dict[str, Any], *, target_date: date
    ) -> dict[str, Any]:
        return {
            "date": target_date,
            "summary": (
                f"{progress['completed_tasks']} of {progress['total_tasks']} tasks completed. "
                f"Completion rate was {progress['completion_percentage']}%."
            ),
            "recommendations": (
                "Review remaining work and schedule the next highest-priority task first."
            ),
            "productivity_score": progress["productivity_score"],
        }

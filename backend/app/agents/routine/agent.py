from __future__ import annotations

from datetime import date
from typing import Any

from app.agents.routine.tools import ALLOWED_TOOLS
from app.providers.base import BaseProvider
from app.providers.factory import get_provider


class RoutineAgent:
    """Deterministic routine agent with explicit tool allowlist."""

    def __init__(self, provider: BaseProvider | None = None):
        self.allowed_tools = set(ALLOWED_TOOLS)
        self.provider = provider or get_provider()

    def execute(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        if tool_name not in self.allowed_tools:
            raise ValueError(f"Tool '{tool_name}' is not allowed")
        return ALLOWED_TOOLS[tool_name](*args, **kwargs)

    def plan_day(self, planned_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        created = []
        for payload in planned_tasks:
            created.append(self.execute("create_task", payload))
        return created

    def review_day(self, target_date: date) -> dict[str, Any]:
        progress = self.execute("get_daily_progress", target_date)
        review = self.provider.generate_daily_review(progress, target_date=target_date)
        return {"progress": progress, "review": review}

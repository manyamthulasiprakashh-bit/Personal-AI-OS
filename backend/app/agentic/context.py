from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.api.dependencies import CurrentUser


@dataclass
class BudgetState:
    max_iterations: int
    max_tool_calls: int
    max_planner_failures: int
    max_repeated_identical_calls: int
    planner_failures: int = 0
    repeated_calls: dict[str, int] = field(default_factory=dict)


@dataclass
class AgentExecutionContext:
    run_id: str
    user_id: str
    current_user: CurrentUser
    correlation_id: str
    budget: BudgetState
    cancelled: bool = False
    approval_context: dict[str, Any] = field(default_factory=dict)

from __future__ import annotations

from typing import Any


EVENT_TYPES = frozenset(
    {
        "agent_run_started",
        "planner_started",
        "planner_completed",
        "planner_failed",
        "plan_created",
        "tool_selected",
        "tool_started",
        "tool_completed",
        "tool_failed",
        "observation_received",
        "replan_started",
        "approval_requested",
        "approval_received",
        "user_input_requested",
        "agent_completed",
        "agent_failed",
        "agent_cancelled",
    }
)


def event_data(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}

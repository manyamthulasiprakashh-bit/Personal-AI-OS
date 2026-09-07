from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RunStatus = Literal[
    "queued",
    "running",
    "waiting_for_approval",
    "waiting_for_user",
    "completed",
    "failed",
    "cancelled",
    "expired",
]
DecisionType = Literal[
    "call_tool",
    "complete",
    "ask_user",
    "request_approval",
    "replan",
    "fail",
]


class PlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = Field(default=None, max_length=2000)
    question: str | None = Field(default=None, max_length=2000)


class PlannerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    iteration: int = 0
    tool_call_count: int = 0
    observations: list[dict[str, Any]] = Field(default_factory=list)
    completed_tools: list[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RunStatus
    summary: str | None = None
    observations: list[dict[str, Any]] = Field(default_factory=list)

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=4000)


class AgentApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool


class AgentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    event_type: str
    iteration: int
    data: dict[str, Any]
    created_at: datetime


class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tool: str
    status: str
    content: dict[str, Any] | None
    error: dict[str, Any] | None
    metadata_json: dict[str, Any]
    created_at: datetime


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    error: dict[str, Any] | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    observation: ObservationResponse | None


class PlanStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    capability: str
    arguments: dict[str, Any]
    status: str
    attempt_count: int
    result_reference: str | None
    tool_calls: list[ToolCallResponse]


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    goal: str
    status: Literal[
        "queued",
        "running",
        "waiting_for_approval",
        "waiting_for_user",
        "completed",
        "failed",
        "cancelled",
        "expired",
    ]
    current_iteration: int
    planner_call_count: int
    tool_call_count: int
    plan_version: int
    failure_summary: str | None
    completion_summary: str | None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None
    plan_steps: list[PlanStepResponse]
    events: list[AgentEventResponse]

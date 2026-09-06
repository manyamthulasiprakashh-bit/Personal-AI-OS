from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LearningGoalStatus = Literal["active", "completed", "archived"]
LearningPriority = Literal["low", "medium", "high"]
LearningResourceStatus = Literal["active", "completed", "archived"]


class LearningGoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: LearningGoalStatus = "active"
    priority: LearningPriority = "medium"
    target_date: date | None = None


class LearningGoalResponse(LearningGoalCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class LearningSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int = Field(..., ge=1, le=1440)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_time_order(self) -> "LearningSessionCreate":
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at must not be earlier than started_at")
        return self


class LearningSessionResponse(LearningSessionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime


class LearningResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str | None = None
    title: str = Field(..., min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    resource_type: str = Field(default="reference", min_length=1, max_length=50)
    status: LearningResourceStatus = "active"


class LearningResourceResponse(LearningResourceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime


class LearningProgress(BaseModel):
    goal_id: str | None = None
    total_goals: int
    active_goals: int
    completed_goals: int
    total_sessions: int
    total_minutes: int


class LearningRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: str | None = None


class LearningRecommendation(BaseModel):
    summary: str
    observations: list[str]
    recommendations: list[str]
    next_steps: list[str]


class LearningAgentResponse(BaseModel):
    progress: LearningProgress
    recommendation: LearningRecommendation

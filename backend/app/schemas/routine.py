from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskCategory = Literal["learning", "coding", "project", "job", "exercise", "personal", "other"]
TaskPriority = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal["pending", "in_progress", "completed", "skipped"]

VALID_CATEGORIES = {"learning", "coding", "project", "job", "exercise", "personal", "other"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {"pending", "in_progress", "completed", "skipped"}


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: TaskCategory = "other"
    priority: TaskPriority = "medium"
    status: TaskStatus = "pending"
    planned_date: date | None = None
    planned_start_time: time | None = None
    planned_end_time: time | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError("invalid category")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in VALID_PRIORITIES:
            raise ValueError("invalid priority")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError("invalid status")
        return value


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: TaskCategory | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    planned_date: date | None = None
    planned_start_time: time | None = None
    planned_end_time: time | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    actual_minutes: int | None = Field(default=None, ge=0, le=1440)


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actual_minutes: int | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class HabitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    target_frequency: str = Field(default="daily", max_length=50)
    active: bool = True


class HabitCreate(HabitBase):
    pass


class HabitResponse(HabitBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class HabitLogCreate(BaseModel):
    date: date
    completed: bool = False
    notes: str | None = None


class HabitLogResponse(HabitLogCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    habit_id: str
    created_at: datetime


class ActivityCreate(BaseModel):
    task_id: str | None = None
    category: TaskCategory = "other"
    description: str = Field(..., min_length=1, max_length=500)
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError("invalid category")
        return value


class ActivityResponse(ActivityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class DailyProgressResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    skipped_tasks: int
    completion_percentage: float
    planned_minutes: int
    actual_minutes: int
    category_breakdown: dict[str, int]
    habit_completion: dict[str, bool]
    productivity_score: int


class AgentReviewResponse(BaseModel):
    progress: DailyProgressResponse
    review: dict[str, Any]


class AgentReviewInput(BaseModel):
    date: date


class DailyReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date
    planned_minutes: int
    completed_minutes: int
    completed_tasks: int
    missed_tasks: int
    productivity_score: int
    summary: str | None = None
    recommendations: str | None = None
    created_at: datetime


class DailyPlanResponse(BaseModel):
    date: date
    tasks: list[TaskResponse]
    habits: list[HabitResponse]
    total_planned_minutes: int


class DailyReviewInput(BaseModel):
    date: date
    planned_minutes: int = Field(ge=0)
    actual_minutes: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    total_tasks: int = Field(ge=0)
    categories: dict[str, int] = Field(default_factory=dict)
    summary: str | None = None
    recommendations: str | None = None

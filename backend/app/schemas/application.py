from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal["applied", "interviewing", "offer", "rejected", "withdrawn"]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    applied_at: datetime | None = None
    notes: str | None = None
    next_action: str | None = None
    next_action_at: datetime | None = None


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus | None = None
    notes: str | None = None
    next_action: str | None = None
    next_action_at: datetime | None = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    job_id: str
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    notes: str | None
    next_action: str | None
    next_action_at: datetime | None

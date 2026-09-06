from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["saved", "reviewing", "archived"]


class JobOpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    location: str | None = Field(default=None, max_length=255)
    work_mode: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    description_snapshot: str | None = None
    notes: str | None = None


class JobOpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    location: str | None = Field(default=None, max_length=255)
    work_mode: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=100)
    description_snapshot: str | None = None
    notes: str | None = None
    status: JobStatus | None = None


class JobOpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    company: str
    url: str | None
    location: str | None
    work_mode: str | None
    source: str | None
    description_snapshot: str | None
    status: JobStatus
    notes: str | None
    saved_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class JobAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    title: str
    company: str
    location: str | None
    work_mode: str | None
    source: str | None
    description_snapshot: str | None
    notes: str | None
    status: JobStatus


class JobAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    extracted_requirements: list[str]
    positive_signals: list[str]
    unknowns: list[str]
    suggested_next_steps: list[str]
    confidence: Literal["low", "medium", "high"]


class JobAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job: JobOpportunityResponse
    analysis: JobAnalysis

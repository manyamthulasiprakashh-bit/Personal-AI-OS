from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import JobOpportunity


class JobRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create(self, payload: dict[str, Any]) -> JobOpportunity:
        job = JobOpportunity(user_id=self.user_id, **payload)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list(self) -> list[JobOpportunity]:
        query = (
            select(JobOpportunity)
            .where(JobOpportunity.user_id == self.user_id)
            .order_by(JobOpportunity.saved_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def get(self, job_id: str) -> JobOpportunity | None:
        query = select(JobOpportunity).where(
            JobOpportunity.id == job_id, JobOpportunity.user_id == self.user_id
        )
        return self.db.execute(query).scalar_one_or_none()

    def update(self, job: JobOpportunity, payload: dict[str, Any]) -> JobOpportunity:
        for key, value in payload.items():
            if value is not None:
                setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job

    def archive(self, job: JobOpportunity) -> JobOpportunity:
        job.status = "archived"
        job.closed_at = datetime.now(timezone.utc)
        job.updated_at = job.closed_at
        self.db.commit()
        self.db.refresh(job)
        return job

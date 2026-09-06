from __future__ import annotations

from app.models.job import JobOpportunity
from app.repositories.job import JobRepository
from app.schemas.job import JobOpportunityCreate, JobOpportunityUpdate


class JobNotFoundError(LookupError):
    pass


class JobValidationError(ValueError):
    pass


class JobService:
    def __init__(self, db, user_id: str):
        self.repository = JobRepository(db, user_id)

    def create(self, payload: JobOpportunityCreate) -> JobOpportunity:
        return self.repository.create(payload.model_dump())

    def list(self) -> list[JobOpportunity]:
        return self.repository.list()

    def get(self, job_id: str) -> JobOpportunity:
        job = self.repository.get(job_id)
        if job is None:
            raise JobNotFoundError
        return job

    def update(self, job_id: str, payload: JobOpportunityUpdate) -> JobOpportunity:
        job = self.get(job_id)
        if job.status == "archived":
            raise JobValidationError("archived jobs cannot be updated")

        changes = payload.model_dump(exclude_none=True)
        requested_status = changes.get("status")
        if requested_status == "archived":
            raise JobValidationError("use the archive operation to archive a job")
        if requested_status == "saved" and job.status != "saved":
            raise JobValidationError("jobs cannot move back to saved")
        if requested_status == "reviewing" and job.status not in {"saved", "reviewing"}:
            raise JobValidationError("invalid job status transition")
        return self.repository.update(job, changes)

    def archive(self, job_id: str) -> JobOpportunity:
        job = self.get(job_id)
        if job.status == "archived":
            return job
        return self.repository.archive(job)

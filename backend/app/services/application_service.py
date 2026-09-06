from __future__ import annotations

from datetime import datetime, timezone

from app.models.application import Application
from app.repositories.application import ApplicationConflictError, ApplicationRepository
from app.repositories.job import JobRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationNotFoundError(LookupError):
    pass


class ApplicationJobNotFoundError(LookupError):
    pass


class ApplicationValidationError(ValueError):
    pass


class ApplicationService:
    _allowed_transitions = {
        "applied": {"interviewing", "rejected", "withdrawn"},
        "interviewing": {"offer", "rejected", "withdrawn"},
        "offer": set(),
        "rejected": set(),
        "withdrawn": set(),
    }

    def __init__(self, db, user_id: str):
        self.application_repository = ApplicationRepository(db, user_id)
        self.job_repository = JobRepository(db, user_id)

    def create(self, payload: ApplicationCreate) -> Application:
        job = self.job_repository.get(payload.job_id)
        if job is None:
            raise ApplicationJobNotFoundError
        if job.status == "archived":
            raise ApplicationValidationError("archived jobs cannot have applications")
        if self.application_repository.get_active_for_job(payload.job_id) is not None:
            raise ApplicationConflictError

        data = payload.model_dump(exclude_none=True)
        data["status"] = "applied"
        data["applied_at"] = payload.applied_at or datetime.now(timezone.utc)
        return self.application_repository.create(data)

    def list(self) -> list[Application]:
        return self.application_repository.list()

    def get(self, application_id: str) -> Application:
        application = self.application_repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError
        return application

    def update(self, application_id: str, payload: ApplicationUpdate) -> Application:
        application = self.get(application_id)
        changes = payload.model_dump(exclude_unset=True)
        requested_status = changes.get("status")
        if requested_status is not None and requested_status != application.status:
            allowed = self._allowed_transitions[application.status]
            if requested_status not in allowed:
                raise ApplicationValidationError("invalid application status transition")
        return self.application_repository.update(application, changes)

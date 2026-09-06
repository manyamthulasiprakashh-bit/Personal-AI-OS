from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import ACTIVE_APPLICATION_STATUSES, Application


class ApplicationConflictError(RuntimeError):
    pass


class ApplicationRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create(self, payload: dict[str, Any]) -> Application:
        application = Application(user_id=self.user_id, **payload)
        self.db.add(application)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ApplicationConflictError from error
        self.db.refresh(application)
        return application

    def list(self) -> list[Application]:
        query = (
            select(Application)
            .where(Application.user_id == self.user_id)
            .order_by(Application.updated_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def get(self, application_id: str) -> Application | None:
        query = select(Application).where(
            Application.id == application_id, Application.user_id == self.user_id
        )
        return self.db.execute(query).scalar_one_or_none()

    def get_active_for_job(self, job_id: str) -> Application | None:
        query = select(Application).where(
            Application.job_id == job_id,
            Application.user_id == self.user_id,
            Application.status.in_(ACTIVE_APPLICATION_STATUSES),
        )
        return self.db.execute(query).scalar_one_or_none()

    def update(self, application: Application, payload: dict[str, Any]) -> Application:
        for key, value in payload.items():
            setattr(application, key, value)
        application.updated_at = datetime.now(timezone.utc)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ApplicationConflictError from error
        self.db.refresh(application)
        return application

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.session import Base
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.job import JobOpportunityCreate
from app.services.application_service import (
    ApplicationConflictError,
    ApplicationJobNotFoundError,
    ApplicationService,
    ApplicationValidationError,
)
from app.services.job_service import JobService


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def create_user(db, email):
    user = User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_job(db, user):
    return JobService(db, user.id).create(
        JobOpportunityCreate(title="Backend Engineer", company="Example Inc")
    )


def test_service_rejects_duplicate_active_application(db):
    user = create_user(db, "application-service-duplicate@example.com")
    job = create_job(db, user)
    service = ApplicationService(db, user.id)
    service.create(ApplicationCreate(job_id=job.id))

    with pytest.raises(ApplicationConflictError):
        service.create(ApplicationCreate(job_id=job.id))


def test_service_rejects_missing_job_and_invalid_transitions(db):
    user = create_user(db, "application-service-transition@example.com")
    service = ApplicationService(db, user.id)

    with pytest.raises(ApplicationJobNotFoundError):
        service.create(ApplicationCreate(job_id="missing"))

    job = create_job(db, user)
    application = service.create(ApplicationCreate(job_id=job.id))
    service.update(application.id, ApplicationUpdate(status="interviewing"))

    with pytest.raises(ApplicationValidationError):
        service.update(application.id, ApplicationUpdate(status="applied"))

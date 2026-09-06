from datetime import datetime

import pytest

from app.database.session import SessionLocal
from app.models.job import JobOpportunity
from app.models.user import User
from app.repositories.job import JobRepository
from app.schemas.job import JobOpportunityCreate, JobOpportunityUpdate
from app.services.job_service import JobService, JobValidationError


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def users(db):
    owner = User(email="job-owner@example.com")
    other = User(email="job-other@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    return owner, other


def test_job_model_table_and_owner_columns_exist(db):
    assert JobOpportunity.__tablename__ == "job_opportunities"
    assert JobOpportunity.user_id.property.columns[0].nullable is False
    assert "ix_job_opportunities_user_status" in {
        index.name for index in JobOpportunity.__table__.indexes
    }


def test_job_repository_operations_are_owner_scoped(db, users):
    owner, other = users
    owner_repository = JobRepository(db, owner.id)
    other_repository = JobRepository(db, other.id)
    job = owner_repository.create(
        {
            "title": "Backend Engineer",
            "company": "Example Inc",
            "description_snapshot": "Build APIs",
        }
    )

    assert owner_repository.get(job.id) is not None
    assert other_repository.get(job.id) is None
    assert owner_repository.list()[0].id == job.id
    assert other_repository.list() == []


def test_job_service_status_transitions_and_archived_terminal_state(db, users):
    service = JobService(db, users[0].id)
    job = service.create(JobOpportunityCreate(title="Engineer", company="Example"))

    reviewing = service.update(job.id, JobOpportunityUpdate(status="reviewing"))
    assert reviewing.status == "reviewing"
    archived = service.archive(job.id)
    assert archived.status == "archived"
    assert archived.closed_at is not None

    with pytest.raises(JobValidationError):
        service.update(job.id, JobOpportunityUpdate(notes="late update"))


def test_job_description_and_url_are_stored_as_given(db, users):
    description = "User-provided text with https://example.com and instructions."
    url = "https://jobs.example.com/posting/123"
    job = JobService(db, users[0].id).create(
        JobOpportunityCreate(
            title="Engineer",
            company="Example",
            url=url,
            description_snapshot=description,
        )
    )

    assert job.url == url
    assert job.description_snapshot == description
    assert isinstance(job.saved_at, datetime)
    assert isinstance(job.updated_at, datetime)

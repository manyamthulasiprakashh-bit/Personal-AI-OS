from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import CurrentUser, get_current_user
from app.api.routes.application import get_application_service
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User
from app.schemas.application import ApplicationCreate
from app.services.application_service import ApplicationService
from app.schemas.job import JobOpportunityCreate
from app.services.job_service import JobService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def with_user(user):
    return lambda: CurrentUser(user.id, user.email)


def create_user(db, email):
    user = User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_job(db, user, title="Backend Engineer"):
    return JobService(db, user.id).create(JobOpportunityCreate(title=title, company="Example Inc"))


def create_application(db, user, job):
    return ApplicationService(db, user.id).create(ApplicationCreate(job_id=job.id))


def override_user_and_service(user, db):
    app.dependency_overrides[get_current_user] = with_user(user)
    app.dependency_overrides[get_application_service] = lambda: ApplicationService(db, user.id)


def clear_overrides():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_application_service, None)


def test_create_application_assigns_owner_and_applied_status(client, db):
    user = create_user(db, "application-owner@example.com")
    job = create_job(db, user)
    override_user_and_service(user, db)
    try:
        response = client.post(
            "/api/applications",
            json={
                "job_id": job.id,
                "notes": "Submitted through the company portal",
                "next_action": "Follow up",
            },
        )
    finally:
        clear_overrides()

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user_id"] == user.id
    assert body["job_id"] == job.id
    assert body["status"] == "applied"
    assert body["notes"] == "Submitted through the company portal"


def test_create_application_rejects_archived_and_foreign_jobs(client, db):
    owner = create_user(db, "application-archive-owner@example.com")
    other = create_user(db, "application-archive-other@example.com")
    archived_job = create_job(db, owner, "Archived Engineer")
    JobService(db, owner.id).archive(archived_job.id)
    foreign_job = create_job(db, other, "Private Engineer")
    override_user_and_service(owner, db)
    try:
        archived = client.post("/api/applications", json={"job_id": archived_job.id})
        foreign = client.post("/api/applications", json={"job_id": foreign_job.id})
    finally:
        clear_overrides()

    assert archived.status_code == 400
    assert foreign.status_code == 404


def test_duplicate_active_application_returns_conflict(client, db):
    user = create_user(db, "application-duplicate@example.com")
    job = create_job(db, user)
    create_application(db, user, job)
    override_user_and_service(user, db)
    try:
        response = client.post("/api/applications", json={"job_id": job.id})
    finally:
        clear_overrides()

    assert response.status_code == 409


def test_list_is_owner_scoped_and_ordered_by_updated_at(client, db):
    owner = create_user(db, "application-list-owner@example.com")
    other = create_user(db, "application-list-other@example.com")
    first = create_application(db, owner, create_job(db, owner, "First Engineer"))
    second = create_application(db, owner, create_job(db, owner, "Second Engineer"))
    create_application(db, other, create_job(db, other, "Other Engineer"))
    second.updated_at = datetime.now(timezone.utc)
    db.commit()
    override_user_and_service(owner, db)
    try:
        response = client.get("/api/applications")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second.id, first.id]


def test_get_foreign_and_missing_application_return_404(client, db):
    owner = create_user(db, "application-get-owner@example.com")
    other = create_user(db, "application-get-other@example.com")
    application = create_application(db, owner, create_job(db, owner))
    override_user_and_service(other, db)
    try:
        foreign = client.get(f"/api/applications/{application.id}")
        missing = client.get("/api/applications/00000000-0000-0000-0000-000000000000")
    finally:
        clear_overrides()

    assert foreign.status_code == 404
    assert missing.status_code == 404


def test_update_application_fields_and_valid_transitions(client, db):
    user = create_user(db, "application-update@example.com")
    application = create_application(db, user, create_job(db, user))
    override_user_and_service(user, db)
    try:
        updated = client.patch(
            f"/api/applications/{application.id}",
            json={
                "status": "interviewing",
                "notes": "Recruiter contacted me",
                "next_action": "Prepare for screen",
                "next_action_at": "2026-09-07T10:00:00Z",
            },
        )
        offer = client.patch(f"/api/applications/{application.id}", json={"status": "offer"})
    finally:
        clear_overrides()

    assert updated.status_code == 200
    assert updated.json()["status"] == "interviewing"
    assert updated.json()["next_action"] == "Prepare for screen"
    assert offer.status_code == 200
    assert offer.json()["status"] == "offer"


def test_applied_to_offer_transition_is_rejected(client, db):
    user = create_user(db, "application-transition-offer@example.com")
    application = create_application(db, user, create_job(db, user))
    override_user_and_service(user, db)
    try:
        response = client.patch(f"/api/applications/{application.id}", json={"status": "offer"})
    finally:
        clear_overrides()

    assert response.status_code == 400


def test_terminal_application_rejects_status_change_but_allows_notes(client, db):
    user = create_user(db, "application-terminal@example.com")
    application = create_application(db, user, create_job(db, user))
    override_user_and_service(user, db)
    try:
        rejected = client.patch(f"/api/applications/{application.id}", json={"status": "rejected"})
        status_change = client.patch(
            f"/api/applications/{application.id}", json={"status": "applied"}
        )
        notes = client.patch(f"/api/applications/{application.id}", json={"notes": "Keep in touch"})
    finally:
        clear_overrides()

    assert rejected.status_code == 200
    assert status_change.status_code == 400
    assert notes.status_code == 200
    assert notes.json()["status"] == "rejected"


@pytest.mark.parametrize(
    "payload",
    [
        {"user_id": "other"},
        {"job_id": "other"},
        {"unexpected": True},
    ],
)
def test_application_schemas_reject_client_controlled_or_unknown_fields(client, db, payload):
    user = create_user(db, "application-validation@example.com")
    job = create_job(db, user)
    override_user_and_service(user, db)
    try:
        if "job_id" in payload:
            response = client.patch(
                "/api/applications/00000000-0000-0000-0000-000000000000", json=payload
            )
        else:
            response = client.post("/api/applications", json={"job_id": job.id, **payload})
    finally:
        clear_overrides()

    assert response.status_code == 422

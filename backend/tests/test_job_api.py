import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User
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


def test_create_job_returns_typed_response(client, db):
    user = User(email="api-job-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = with_user(user)
    try:
        response = client.post(
            "/api/jobs",
            json={
                "title": "Backend Engineer",
                "company": "Example Inc",
                "url": "https://example.com/jobs/1",
                "description_snapshot": "Paste only",
                "notes": "Review later",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["company"] == "Example Inc"
    assert body["status"] == "saved"
    assert body["user_id"] == user.id


def test_job_list_get_and_cross_user_access_are_isolated(client, db):
    owner = User(email="list-job-owner@example.com")
    other = User(email="list-job-other@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    owner_job = JobService(db, owner.id).create(
        JobOpportunityCreate(title="Owner job", company="Owner Co")
    )
    other_job = JobService(db, other.id).create(
        JobOpportunityCreate(title="Other job", company="Other Co")
    )
    app.dependency_overrides[get_current_user] = with_user(owner)
    try:
        listed = client.get("/api/jobs")
        owned = client.get(f"/api/jobs/{owner_job.id}")
        cross_user = client.get(f"/api/jobs/{other_job.id}")
        missing = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [owner_job.id]
    assert owned.status_code == 200
    assert cross_user.status_code == 404
    assert missing.status_code == 404


def test_update_and_archive_job_are_owner_scoped(client, db):
    owner = User(email="update-job-owner@example.com")
    other = User(email="update-job-other@example.com")
    db.add_all([owner, other])
    db.commit()
    db.refresh(owner)
    db.refresh(other)
    job = JobService(db, owner.id).create(JobOpportunityCreate(title="Engineer", company="Example"))
    app.dependency_overrides[get_current_user] = with_user(owner)
    try:
        updated = client.patch(f"/api/jobs/{job.id}", json={"notes": "Updated"})
        archived = client.post(f"/api/jobs/{job.id}/archive")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert updated.status_code == 200
    assert updated.json()["notes"] == "Updated"
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    app.dependency_overrides[get_current_user] = with_user(other)
    try:
        cross_update = client.patch(f"/api/jobs/{job.id}", json={"notes": "Nope"})
        cross_archive = client.post(f"/api/jobs/{job.id}/archive")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert cross_update.status_code == 404
    assert cross_archive.status_code == 404


@pytest.mark.parametrize(
    "method, path, payload",
    [
        ("post", "/api/jobs", {"title": "Engineer", "company": "Example", "user_id": "bad"}),
        ("post", "/api/jobs", {"title": "Engineer", "company": "Example", "unexpected": True}),
        ("patch", "/api/jobs/not-a-job", {"status": "archived"}),
    ],
)
def test_job_requests_reject_unknown_or_client_controlled_fields(client, method, path, payload):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        "validation-user", "validation@example.com"
    )
    try:
        response = getattr(client, method)(path, json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code in {400, 404, 422}
    if method == "post":
        assert response.status_code == 422


def test_archived_status_is_not_arbitrarily_set_by_patch(client, db):
    user = User(email="status-job-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    job = JobService(db, user.id).create(JobOpportunityCreate(title="Engineer", company="Example"))
    app.dependency_overrides[get_current_user] = with_user(user)
    try:
        response = client.patch(f"/api/jobs/{job.id}", json={"status": "archived"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 400


def test_job_url_is_inert_and_no_network_call_is_made(client, db, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    user = User(email="network-job-owner@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    app.dependency_overrides[get_current_user] = with_user(user)
    try:
        response = client.post(
            "/api/jobs",
            json={
                "title": "Engineer",
                "company": "Example",
                "url": "https://example.com/job",
                "description_snapshot": "User-provided snapshot",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    assert response.json()["description_snapshot"] == "User-provided snapshot"

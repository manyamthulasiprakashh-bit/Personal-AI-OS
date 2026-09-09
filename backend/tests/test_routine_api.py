from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User


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


@pytest.fixture
def user_a(db):
    user = User(email=f"routine-a-{datetime.utcnow().timestamp()}@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db):
    user = User(email=f"routine-b-{datetime.utcnow().timestamp()}@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def as_user(user):
    return lambda: CurrentUser(user.id, user.email)


def _create_task(client, user, title="Python practice", planned_date=None):
    payload = {
        "title": title,
        "description": "Two hours of Python study",
        "category": "learning",
        "priority": "high",
        "status": "pending",
        "planned_date": planned_date or str(date.today()),
        "estimated_minutes": 120,
    }
    app.dependency_overrides[get_current_user] = as_user(user)
    try:
        response = client.post("/api/tasks", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 201, response.text
    return response.json()


def _create_habit(client, user, name="Morning reading"):
    app.dependency_overrides[get_current_user] = as_user(user)
    try:
        response = client.post(
            "/api/habits",
            json={"name": name, "target_frequency": "daily"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task_and_list(client, user_a):
    body = _create_task(client, user_a)
    assert body["title"] == "Python practice"
    assert body["category"] == "learning"
    assert body["user_id"] == user_a.id

    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        list_response = client.get("/api/tasks")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert list_response.status_code == 200
    assert any(item["title"] == "Python practice" for item in list_response.json())


def test_complete_task_and_progress(client, user_a):
    task = _create_task(client, user_a, title="DSA review")

    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        complete_response = client.post(f"/api/tasks/{task['id']}/complete")
        progress = client.get("/api/routine/progress", params={"target_date": str(date.today())})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert progress.status_code == 200
    assert progress.json()["completed_tasks"] >= 1


def test_create_habit_and_log(client, user_a):
    habit = _create_habit(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        log_response = client.post(
            f"/api/habits/{habit['id']}/log",
            json={"date": str(date.today()), "completed": True},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert log_response.status_code == 201


def test_activity_creation_and_review_endpoint(client, user_a):
    activity_payload = {
        "category": "learning",
        "description": "Python revision block",
        "started_at": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        "ended_at": datetime.utcnow().isoformat(),
        "duration_minutes": 30,
    }
    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        created = client.post("/api/activities", json=activity_payload)
        review_response = client.post(
            "/api/routine/review",
            json={
                "date": str(date.today()),
                "planned_minutes": 180,
                "actual_minutes": 120,
                "completed_tasks": 2,
                "total_tasks": 3,
                "categories": {"learning": 120},
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert created.status_code == 201
    assert review_response.status_code == 200
    assert review_response.json()["date"] == str(date.today())


def test_missing_task_404(client, user_a):
    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        response = client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 404


def test_invalid_task_payload(client, user_a):
    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        response = client.post("/api/tasks", json={"title": "", "category": "invalid"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 422


# ---------- Phase 8C ownership tests ----------


def test_cross_user_task_get_returns_404(client, user_a, user_b):
    task = _create_task(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.get(f"/api/tasks/{task['id']}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_task_patch_returns_404(client, user_a, user_b):
    task = _create_task(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.patch(f"/api/tasks/{task['id']}", json={"title": "hijacked"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_task_complete_returns_404(client, user_a, user_b):
    task = _create_task(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.post(f"/api/tasks/{task['id']}/complete")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_task_skip_returns_404(client, user_a, user_b):
    task = _create_task(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.post(f"/api/tasks/{task['id']}/skip")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_task_list_isolation(client, user_a, user_b):
    _create_task(client, user_a, title="A's private task")

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.get("/api/tasks")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert all(item["title"] != "A's private task" for item in response.json())


def test_cross_user_habit_log_returns_404(client, user_a, user_b):
    habit = _create_habit(client, user_a)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.post(
            f"/api/habits/{habit['id']}/log",
            json={"date": str(date.today()), "completed": True},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_cross_user_activity_against_foreign_task_returns_404(client, user_a, user_b):
    task = _create_task(client, user_a)

    activity_payload = {
        "task_id": task["id"],
        "category": "learning",
        "description": "attempted hijack",
        "started_at": datetime.utcnow().isoformat(),
        "duration_minutes": 15,
    }
    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response = client.post("/api/activities", json=activity_payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_daily_plan_contains_only_own_data(client, user_a, user_b):
    _create_task(client, user_a, title="A's plan task")
    _create_task(client, user_b, title="B's plan task")

    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        response_a = client.get("/api/routine/today")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response_b = client.get("/api/routine/today")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response_a.status_code == 200
    titles_a = {t["title"] for t in response_a.json()["tasks"]}
    assert "A's plan task" in titles_a
    assert "B's plan task" not in titles_a

    assert response_b.status_code == 200
    titles_b = {t["title"] for t in response_b.json()["tasks"]}
    assert "B's plan task" in titles_b
    assert "A's plan task" not in titles_b


def test_daily_reviews_are_isolated_per_user(client, user_a, user_b):
    payload = {
        "date": str(date.today()),
        "planned_minutes": 60,
        "actual_minutes": 60,
        "completed_tasks": 1,
        "total_tasks": 1,
        "categories": {},
    }
    app.dependency_overrides[get_current_user] = as_user(user_a)
    try:
        response_a = client.post("/api/routine/review", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    app.dependency_overrides[get_current_user] = as_user(user_b)
    try:
        response_b = client.post("/api/routine/review", json=payload)
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    # Both users get their own review for the same date (no global uniqueness conflict)
    assert response_a.json()["date"] == str(date.today())
    assert response_b.json()["date"] == str(date.today())

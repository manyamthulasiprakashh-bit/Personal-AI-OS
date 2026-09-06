from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_task_and_list():
    payload = {
        "title": "Python practice",
        "description": "Two hours of Python study",
        "category": "learning",
        "priority": "high",
        "status": "pending",
        "planned_date": str(date.today()),
        "estimated_minutes": 120,
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["category"] == "learning"

    list_response = client.get("/api/tasks")
    assert list_response.status_code == 200
    assert any(item["title"] == payload["title"] for item in list_response.json())


def test_complete_task_and_progress():
    task_payload = {
        "title": "DSA review",
        "description": "Today’s DSA work",
        "category": "coding",
        "priority": "medium",
        "status": "pending",
        "planned_date": str(date.today()),
        "estimated_minutes": 60,
    }
    created = client.post("/api/tasks", json=task_payload)
    task_id = created.json()["id"]

    complete_response = client.post(f"/api/tasks/{task_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    progress = client.get("/api/routine/progress", params={"target_date": str(date.today())})
    assert progress.status_code == 200
    assert progress.json()["completed_tasks"] >= 1


def test_create_habit_and_log():
    habit_response = client.post(
        "/api/habits",
        json={"name": "Exercise", "description": "30 minute walk", "target_frequency": "daily"},
    )
    assert habit_response.status_code == 201
    habit_id = habit_response.json()["id"]

    log_response = client.post(
        f"/api/habits/{habit_id}/log",
        json={"date": str(date.today()), "completed": True, "notes": "Workout complete"},
    )
    assert log_response.status_code == 201
    assert log_response.json()["completed"] is True


def test_activity_creation_and_review_endpoint():
    activity_payload = {
        "category": "learning",
        "description": "Python revision block",
        "started_at": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
        "ended_at": datetime.utcnow().isoformat(),
        "duration_minutes": 30,
    }
    created = client.post("/api/activities", json=activity_payload)
    assert created.status_code == 201

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
    assert review_response.status_code == 200
    assert review_response.json()["date"] == str(date.today())


def test_missing_task_404():
    response = client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_invalid_task_payload():
    response = client.post("/api/tasks", json={"title": "", "category": "invalid"})
    assert response.status_code == 422

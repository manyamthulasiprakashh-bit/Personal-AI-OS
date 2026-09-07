from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_endpoint() -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert "today" in payload
    assert "agent_activity" in payload


def test_health_reports_database_failure_without_internal_details() -> None:
    def failing_db():
        class BrokenSession:
            def execute(self, statement):
                raise SQLAlchemyError("private database details")

        yield BrokenSession()

    app.dependency_overrides[get_db] = failing_db
    try:
        response = client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "personal-ai-os-backend",
        "database": "unavailable",
    }

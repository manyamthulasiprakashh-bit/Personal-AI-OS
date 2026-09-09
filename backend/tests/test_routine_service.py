from datetime import date

from app.services.routine_service import RoutineService


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


class DummyDB:
    def __init__(self):
        self.items = []
        self.queries = []

    def get(self, model, id):
        for item in self.items:
            if getattr(item, "id", None) == id:
                return item
        return None

    def query(self, model):
        self.queries.append(model)
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


def test_calculate_daily_progress_uses_task_status() -> None:
    service = RoutineService(DummyDB(), TEST_USER_ID)
    tasks = [
        type(
            "Task",
            (),
            {
                "status": "completed",
                "actual_minutes": 60,
                "estimated_minutes": 60,
                "category": "learning",
            },
        )(),
        type(
            "Task",
            (),
            {
                "status": "pending",
                "actual_minutes": None,
                "estimated_minutes": 90,
                "category": "project",
            },
        )(),
        type(
            "Task",
            (),
            {"status": "skipped", "actual_minutes": 0, "estimated_minutes": 30, "category": "job"},
        )(),
    ]

    service.repository.list_tasks = lambda planned_date=None: tasks
    service.repository.list_habits = lambda: []

    progress = service.calculate_daily_progress(date.today())

    assert progress["total_tasks"] == 3
    assert progress["completed_tasks"] == 1
    assert progress["skipped_tasks"] == 1
    assert progress["completion_percentage"] == 33.3
    assert progress["planned_minutes"] == 180
    assert progress["actual_minutes"] == 60

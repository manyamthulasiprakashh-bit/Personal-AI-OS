from __future__ import annotations

from datetime import date
from typing import Any, Callable

from app.database.session import SessionLocal
from app.services.routine_service import RoutineService


def _get_service() -> RoutineService:
    db = SessionLocal()
    try:
        return RoutineService(db)
    finally:
        db.close()


def create_task(payload: dict[str, Any]) -> dict[str, Any]:
    service = _get_service()
    task = service.create_task(payload)
    return {"id": task.id, "title": task.title, "status": task.status}


def update_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    service = _get_service()
    task = service.update_task(task_id, payload)
    return {"id": task.id, "title": task.title, "status": task.status}


def complete_task(task_id: str) -> dict[str, Any]:
    service = _get_service()
    task = service.complete_task(task_id)
    return {"id": task.id, "status": task.status}


def log_activity(payload: dict[str, Any]) -> dict[str, Any]:
    service = _get_service()
    activity = service.log_activity(payload)
    return {
        "id": activity.id,
        "description": activity.description,
        "duration_minutes": activity.duration_minutes,
    }


def get_daily_plan(target_date: date) -> dict[str, Any]:
    service = _get_service()
    plan = service.get_daily_plan(target_date)
    return {
        "date": plan["date"].isoformat(),
        "total_planned_minutes": plan["total_planned_minutes"],
    }


def get_daily_progress(target_date: date) -> dict[str, Any]:
    service = _get_service()
    return service.calculate_daily_progress(target_date)


def generate_daily_review(target_date: date) -> dict[str, Any]:
    service = _get_service()
    review = service.generate_daily_review(target_date)
    return {
        "id": review.id,
        "date": review.date.isoformat(),
        "summary": review.summary,
        "recommendations": review.recommendations,
        "productivity_score": review.productivity_score,
    }


ALLOWED_TOOLS: dict[str, Callable[..., Any]] = {
    "create_task": create_task,
    "update_task": update_task,
    "complete_task": complete_task,
    "log_activity": log_activity,
    "get_daily_plan": get_daily_plan,
    "get_daily_progress": get_daily_progress,
    "generate_daily_review": generate_daily_review,
}

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.routine import DailyActivity, DailyReview, Habit, HabitLog, Task
from app.repositories.routine import RoutineRepository


class RoutineService:
    def __init__(self, db: Session, user_id: str):
        self.repository = RoutineRepository(db, user_id)
        self.db = db
        self.user_id = user_id

    def create_task(self, payload: dict[str, Any]) -> Task:
        if payload.get("title") is None or not str(payload["title"]).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="task title is required"
            )
        if payload.get("estimated_minutes") is not None and payload["estimated_minutes"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="estimated_minutes must be greater than zero",
            )
        return self.repository.create_task(payload)

    def get_task(self, task_id: str) -> Task:
        task = self.repository.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return task

    def list_tasks(self, *, planned_date: date | None = None) -> list[Task]:
        return self.repository.list_tasks(planned_date=planned_date)

    def update_task(self, task_id: str, payload: dict[str, Any]) -> Task:
        task = self.get_task(task_id)
        if payload.get("status") in {"completed", "skipped"}:
            if payload.get("completed_at") is None:
                payload["completed_at"] = datetime.now(timezone.utc)
        return self.repository.update_task(task, payload)

    def complete_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.status == "completed":
            return task
        if task.status == "skipped":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="cannot complete a skipped task"
            )
        payload = {
            "status": "completed",
            "actual_minutes": task.actual_minutes or task.estimated_minutes or 0,
            "completed_at": datetime.now(timezone.utc),
        }
        return self.repository.update_task(task, payload)

    def skip_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.status == "skipped":
            return task
        payload = {"status": "skipped", "completed_at": datetime.now(timezone.utc)}
        return self.repository.update_task(task, payload)

    def create_habit(self, payload: dict[str, Any]) -> Habit:
        if payload.get("name") is None or not str(payload["name"]).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="habit name is required"
            )
        return self.repository.create_habit(payload)

    def list_habits(self) -> list[Habit]:
        return self.repository.list_habits()

    def log_habit(self, habit_id: str, payload: dict[str, Any]) -> HabitLog:
        habit = self.repository.get_habit(habit_id)
        if habit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="habit not found")
        log_payload = {"habit_id": habit_id, **payload}
        return self.repository.log_habit(log_payload)

    def log_activity(self, payload: dict[str, Any]) -> DailyActivity:
        if payload.get("description") is None or not str(payload["description"]).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="activity description is required"
            )
        if payload.get("duration_minutes") is not None and payload["duration_minutes"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_minutes must be greater than zero",
            )
        task_id = payload.get("task_id")
        if task_id is not None and self.repository.get_task(task_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
        return self.repository.log_activity(payload)

    def list_activities(self, planned_date: date | None = None) -> list[DailyActivity]:
        return self.repository.list_activities(planned_date=planned_date)

    def get_daily_plan(self, target_date: date) -> dict[str, Any]:
        tasks = self.repository.list_tasks(planned_date=target_date)
        habits = self.repository.list_habits()
        total_planned_minutes = sum((task.estimated_minutes or 0) for task in tasks)
        return {
            "date": target_date,
            "tasks": tasks,
            "habits": habits,
            "total_planned_minutes": total_planned_minutes,
        }

    def calculate_daily_progress(self, target_date: date) -> dict[str, Any]:
        tasks = self.repository.list_tasks(planned_date=target_date)
        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        skipped_tasks = sum(1 for task in tasks if task.status == "skipped")
        pending_tasks = sum(1 for task in tasks if task.status in {"pending", "in_progress"})
        completion_percentage = (
            round((completed_tasks / total_tasks * 100), 1) if total_tasks else 0.0
        )
        planned_minutes = sum((task.estimated_minutes or 0) for task in tasks)
        actual_minutes = sum(
            (task.actual_minutes or 0) for task in tasks if task.status == "completed"
        )
        category_breakdown: dict[str, int] = {}
        for task in tasks:
            category_breakdown[task.category] = category_breakdown.get(task.category, 0) + int(
                task.actual_minutes or task.estimated_minutes or 0
            )

        habits = self.repository.list_habits()
        habit_completion: dict[str, bool] = {}
        for habit in habits:
            logs = self.repository.list_habit_logs_for_date(habit.id, target_date)
            habit_completion[habit.name] = any(log.completed for log in logs) if logs else False

        productivity_score = max(
            0, min(100, int((completed_tasks / total_tasks * 100) if total_tasks else 0))
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "skipped_tasks": skipped_tasks,
            "completion_percentage": completion_percentage,
            "planned_minutes": planned_minutes,
            "actual_minutes": actual_minutes,
            "category_breakdown": category_breakdown,
            "habit_completion": habit_completion,
            "productivity_score": productivity_score,
        }

    def generate_daily_review(self, target_date: date) -> DailyReview:
        progress = self.calculate_daily_progress(target_date)
        summary = (
            f"{progress['completed_tasks']} of {progress['total_tasks']} tasks completed. "
            f"Completion rate was {progress['completion_percentage']}%."
        )
        recommendations = "Review remaining work and schedule the next highest-priority task first."
        existing = self.repository.get_daily_review(target_date)
        if existing:
            return existing

        payload = {
            "date": target_date,
            "planned_minutes": progress["planned_minutes"],
            "completed_minutes": progress["actual_minutes"],
            "completed_tasks": progress["completed_tasks"],
            "missed_tasks": progress["pending_tasks"] + progress["skipped_tasks"],
            "productivity_score": progress["productivity_score"],
            "summary": summary,
            "recommendations": recommendations,
        }
        return self.repository.create_daily_review(payload)

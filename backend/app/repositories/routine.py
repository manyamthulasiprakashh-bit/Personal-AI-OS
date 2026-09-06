from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.routine import DailyActivity, DailyReview, Habit, HabitLog, Task


class RoutineRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, payload: dict[str, Any]) -> Task:
        task = Task(**payload)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self.db.get(Task, task_id)

    def list_tasks(self, *, planned_date: date | None = None) -> list[Task]:
        query = select(Task).order_by(
            Task.planned_date.asc(), Task.priority.desc(), Task.created_at.asc()
        )
        if planned_date is not None:
            query = query.where(Task.planned_date == planned_date)
        return list(self.db.execute(query).scalars().all())

    def update_task(self, task: Task, payload: dict[str, Any]) -> Task:
        for key, value in payload.items():
            if value is not None:
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def create_habit(self, payload: dict[str, Any]) -> Habit:
        habit = Habit(**payload)
        self.db.add(habit)
        self.db.commit()
        self.db.refresh(habit)
        return habit

    def list_habits(self) -> list[Habit]:
        query = select(Habit).order_by(Habit.created_at.asc())
        return list(self.db.execute(query).scalars().all())

    def log_habit(self, payload: dict[str, Any]) -> HabitLog:
        log = HabitLog(**payload)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def log_activity(self, payload: dict[str, Any]) -> DailyActivity:
        activity = DailyActivity(**payload)
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def list_activities(self, *, planned_date: date | None = None) -> list[DailyActivity]:
        query = select(DailyActivity).order_by(DailyActivity.started_at.desc())
        if planned_date is not None:
            query = query.where(
                DailyActivity.started_at >= datetime.combine(planned_date, datetime.min.time())
            )
        return list(self.db.execute(query).scalars().all())

    def create_daily_review(self, payload: dict[str, Any]) -> DailyReview:
        review = DailyReview(**payload)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get_daily_review(self, review_date: date) -> DailyReview | None:
        query = select(DailyReview).where(DailyReview.date == review_date)
        return self.db.execute(query).scalar_one_or_none()

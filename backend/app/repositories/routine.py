from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.routine import DailyActivity, DailyReview, Habit, HabitLog, Task


class RoutineRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_task(self, payload: dict[str, Any]) -> Task:
        task = Task(user_id=self.user_id, **payload)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> Task | None:
        query = select(Task).where(Task.id == task_id, Task.user_id == self.user_id)
        return self.db.execute(query).scalar_one_or_none()

    def list_tasks(self, *, planned_date: date | None = None) -> list[Task]:
        query = (
            select(Task)
            .where(Task.user_id == self.user_id)
            .order_by(Task.planned_date.asc(), Task.priority.desc(), Task.created_at.asc())
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
        habit = Habit(user_id=self.user_id, **payload)
        self.db.add(habit)
        self.db.commit()
        self.db.refresh(habit)
        return habit

    def get_habit(self, habit_id: str) -> Habit | None:
        query = select(Habit).where(Habit.id == habit_id, Habit.user_id == self.user_id)
        return self.db.execute(query).scalar_one_or_none()

    def list_habits(self) -> list[Habit]:
        query = select(Habit).where(Habit.user_id == self.user_id).order_by(Habit.created_at.asc())
        return list(self.db.execute(query).scalars().all())

    def log_habit(self, payload: dict[str, Any]) -> HabitLog:
        log = HabitLog(**payload)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_habit_logs_for_date(self, habit_id: str, target_date: date) -> list[HabitLog]:
        query = select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.date == target_date)
        return list(self.db.execute(query).scalars().all())

    def log_activity(self, payload: dict[str, Any]) -> DailyActivity:
        activity = DailyActivity(user_id=self.user_id, **payload)
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def list_activities(self, *, planned_date: date | None = None) -> list[DailyActivity]:
        query = (
            select(DailyActivity)
            .where(DailyActivity.user_id == self.user_id)
            .order_by(DailyActivity.started_at.desc())
        )
        if planned_date is not None:
            query = query.where(
                DailyActivity.started_at >= datetime.combine(planned_date, datetime.min.time())
            )
        return list(self.db.execute(query).scalars().all())

    def create_daily_review(self, payload: dict[str, Any]) -> DailyReview:
        review = DailyReview(user_id=self.user_id, **payload)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get_daily_review(self, review_date: date) -> DailyReview | None:
        query = select(DailyReview).where(
            DailyReview.date == review_date, DailyReview.user_id == self.user_id
        )
        return self.db.execute(query).scalar_one_or_none()

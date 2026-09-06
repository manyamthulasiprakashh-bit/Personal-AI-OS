from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.user import User


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("title", "planned_date", name="uq_task_title_date"),
        {"schema": None},
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_start_time: Mapped[time | None] = mapped_column(nullable=True)
    planned_end_time: Mapped[time | None] = mapped_column(nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )

    user: Mapped[User | None] = relationship("User", back_populates="tasks")
    activities: Mapped[list["DailyActivity"]] = relationship(back_populates="task")


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="daily")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    logs: Mapped[list["HabitLog"]] = relationship(back_populates="habit")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    habit_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("habits.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    habit: Mapped[Habit] = relationship(back_populates="logs")


class DailyActivity(Base):
    __tablename__ = "daily_activities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    task: Mapped[Task | None] = relationship(back_populates="activities")


class DailyReview(Base):
    __tablename__ = "daily_reviews"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    planned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    productivity_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

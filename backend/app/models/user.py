from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.job import JobOpportunity
    from app.models.learning import LearningGoal, LearningResource, LearningSession
    from app.models.routine import DailyActivity, DailyReview, Habit, Task
    from app.models.auth import AuthSession, UserIdentity
    from app.models.agent_run import AgentRun


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
    habits: Mapped[list["Habit"]] = relationship(back_populates="user")
    daily_reviews: Mapped[list["DailyReview"]] = relationship(back_populates="user")
    daily_activities: Mapped[list["DailyActivity"]] = relationship(back_populates="user")
    learning_goals: Mapped[list["LearningGoal"]] = relationship(back_populates="user")
    learning_sessions: Mapped[list["LearningSession"]] = relationship(back_populates="user")
    learning_resources: Mapped[list["LearningResource"]] = relationship(back_populates="user")
    job_opportunities: Mapped[list["JobOpportunity"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    identities: Mapped[list["UserIdentity"]] = relationship(back_populates="user")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="user")

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.job import JobOpportunity
    from app.models.user import User


ACTIVE_APPLICATION_STATUSES = ("applied", "interviewing", "offer")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_applications_user_updated_at", "user_id", "updated_at"),
        Index("ix_applications_job_id", "job_id"),
        Index(
            "uq_applications_active_user_job",
            "user_id",
            "job_id",
            unique=True,
            postgresql_where=text("status IN ('applied', 'interviewing', 'offer')"),
            sqlite_where=text("status IN ('applied', 'interviewing', 'offer')"),
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("job_opportunities.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship("User", back_populates="applications")
    job: Mapped[JobOpportunity] = relationship("JobOpportunity", back_populates="applications")

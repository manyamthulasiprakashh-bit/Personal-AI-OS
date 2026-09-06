"""Add owner-scoped applications

Revision ID: 20260906_0004
Revises: 20260906_0003
Create Date: 2026-09-06 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260906_0004"
down_revision = "20260906_0003"
branch_labels = None
depends_on = None


ACTIVE_APPLICATION_STATUSES = "status IN ('applied', 'interviewing', 'offer')"


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("job_opportunities.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="applied"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index(
        "ix_applications_user_updated_at", "applications", ["user_id", "updated_at"]
    )
    op.create_index(
        "uq_applications_active_user_job",
        "applications",
        ["user_id", "job_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_APPLICATION_STATUSES),
    )


def downgrade() -> None:
    op.drop_index("uq_applications_active_user_job", table_name="applications")
    op.drop_index("ix_applications_user_updated_at", table_name="applications")
    op.drop_index("ix_applications_job_id", table_name="applications")
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_table("applications")

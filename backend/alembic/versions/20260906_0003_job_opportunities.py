"""Add owner-scoped job opportunities

Revision ID: 20260906_0003
Revises: 20260906_0002
Create Date: 2026-09-06 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260906_0003"
down_revision = "20260906_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("work_mode", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("description_snapshot", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="saved"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_opportunities_user_id", "job_opportunities", ["user_id"])
    op.create_index(
        "ix_job_opportunities_user_status", "job_opportunities", ["user_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_job_opportunities_user_status", table_name="job_opportunities")
    op.drop_index("ix_job_opportunities_user_id", table_name="job_opportunities")
    op.drop_table("job_opportunities")
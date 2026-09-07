"""Add persisted state for the single-agent runtime.

Revision ID: 20260907_0006
Revises: 20260907_0005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260907_0006"
down_revision = "20260907_0005"
branch_labels = None
depends_on = None


def uuid_column(name: str, foreign_key: str | None = None, **kwargs):
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey(foreign_key, ondelete="CASCADE") if foreign_key else None,
        **kwargs,
    )


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        uuid_column("id", primary_key=True, nullable=False),
        uuid_column("user_id", "users.id", nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_iteration", sa.Integer(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("pending_action", sa.JSON(), nullable=True),
        sa.Column("failure_summary", sa.String(length=500), nullable=True),
        sa.Column("completion_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_user_created", "agent_runs", ["user_id", "created_at"])
    op.create_table(
        "agent_plan_steps",
        uuid_column("id", primary_key=True, nullable=False),
        uuid_column("agent_run_id", "agent_runs.id", nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=100), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result_reference", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_agent_plan_steps_agent_run_id", "agent_plan_steps", ["agent_run_id"])
    op.create_table(
        "agent_tool_calls",
        uuid_column("id", primary_key=True, nullable=False),
        uuid_column("plan_step_id", "agent_plan_steps.id", nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_tool_calls_plan_step_id", "agent_tool_calls", ["plan_step_id"])
    op.create_table(
        "agent_observations",
        uuid_column("id", primary_key=True, nullable=False),
        uuid_column("tool_call_id", "agent_tool_calls.id", nullable=False),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tool_call_id", name="uq_agent_observations_tool_call_id"),
    )
    op.create_table(
        "agent_events",
        uuid_column("id", primary_key=True, nullable=False),
        uuid_column("agent_run_id", "agent_runs.id", nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_events_agent_run_id", "agent_events", ["agent_run_id"])
    op.create_index("ix_agent_events_run_sequence", "agent_events", ["agent_run_id", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_agent_events_run_sequence", table_name="agent_events")
    op.drop_index("ix_agent_events_agent_run_id", table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_table("agent_observations")
    op.drop_index("ix_agent_tool_calls_plan_step_id", table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")
    op.drop_index("ix_agent_plan_steps_agent_run_id", table_name="agent_plan_steps")
    op.drop_table("agent_plan_steps")
    op.drop_index("ix_agent_runs_user_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_user_id", table_name="agent_runs")
    op.drop_table("agent_runs")

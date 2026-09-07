"""Track planner calls for agentic runs.

Revision ID: 20260907_0007
Revises: 20260907_0006
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0007"
down_revision = "20260907_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("planner_call_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("agent_runs", "planner_call_count", server_default=None)


def downgrade() -> None:
    op.drop_column("agent_runs", "planner_call_count")
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.agent_run import AgentEvent, AgentRun, Observation, PlanStep, ToolCall


class AgentRunRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_run(self, goal: str) -> AgentRun:
        run = AgentRun(user_id=self.user_id, goal=goal)
        self.db.add(run)
        self.db.flush()
        return run

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.db.execute(
            select(AgentRun)
            .where(AgentRun.id == run_id, AgentRun.user_id == self.user_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(AgentRun.plan_steps)
                .selectinload(PlanStep.tool_calls)
                .selectinload(ToolCall.observation),
                selectinload(AgentRun.events),
            )
        ).scalar_one_or_none()

    def list_runs(self) -> list[AgentRun]:
        return list(
            self.db.execute(
                select(AgentRun)
                .where(AgentRun.user_id == self.user_id)
                .order_by(AgentRun.created_at.desc())
            ).scalars()
        )

    def add_step(self, run: AgentRun, capability: str, arguments: dict[str, Any]) -> PlanStep:
        last_sequence = self.db.scalar(
            select(func.max(PlanStep.sequence)).where(PlanStep.agent_run_id == run.id)
        )
        step = PlanStep(
            agent_run_id=run.id,
            sequence=(last_sequence or 0) + 1,
            capability=capability,
            arguments=arguments,
            status="running",
        )
        self.db.add(step)
        self.db.flush()
        return step

    def add_tool_call(self, step: PlanStep, tool_name: str, arguments: dict[str, Any]) -> ToolCall:
        tool_call = ToolCall(
            plan_step_id=step.id, tool_name=tool_name, arguments=arguments, status="running"
        )
        self.db.add(tool_call)
        self.db.flush()
        return tool_call

    def add_observation(self, tool_call: ToolCall, observation: dict[str, Any]) -> Observation:
        record = Observation(
            tool_call_id=tool_call.id,
            tool=observation["tool"],
            status=observation["status"],
            content=observation.get("result"),
            error=observation.get("error"),
            metadata_json=observation.get("metadata", {}),
        )
        self.db.add(record)
        return record

    def add_event(
        self, run: AgentRun, event_type: str, iteration: int, data: dict[str, Any]
    ) -> AgentEvent:
        last_sequence = self.db.scalar(
            select(func.max(AgentEvent.sequence)).where(AgentEvent.agent_run_id == run.id)
        )
        event = AgentEvent(
            agent_run_id=run.id,
            sequence=(last_sequence or 0) + 1,
            event_type=event_type,
            iteration=iteration,
            data=data,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def commit(self) -> None:
        self.db.commit()

    def set_status(self, run: AgentRun, status: str, **values: Any) -> None:
        run.status = status
        for key, value in values.items():
            setattr(run, key, value)
        run.updated_at = datetime.now(timezone.utc)

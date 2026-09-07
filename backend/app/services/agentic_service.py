from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agentic.context import AgentExecutionContext, BudgetState
from app.agentic.events import event_data
from app.agentic.executor import DirectCapabilityExecutor
from app.agentic.observations import completed_observation, failed_observation
from app.agentic.planner import PlannerProvider, RuleBasedPlanner
from app.agentic.state import PlanDecision, PlannerState
from app.api.dependencies import CurrentUser
from app.repositories.agentic import AgentRunRepository
from app.schemas.agentic import AgentRunResponse


class AgenticRuntimeError(RuntimeError):
    pass


class AgentRunNotFoundError(AgenticRuntimeError):
    pass


class AgentRunStateError(AgenticRuntimeError):
    pass


class AgenticRuntimeService:
    allowed_capabilities = frozenset({"job.analyze", "learning.recommend", "job.learning"})

    def __init__(
        self,
        db: Session,
        current_user: CurrentUser,
        planner: PlannerProvider | None = None,
        executor: DirectCapabilityExecutor | None = None,
        max_iterations: int = 8,
        max_tool_calls: int = 8,
        max_planner_failures: int = 2,
        max_repeated_identical_calls: int = 2,
        tool_timeout_seconds: float = 30.0,
    ):
        self.db = db
        self.current_user = current_user
        self.planner = planner or RuleBasedPlanner()
        self.executor = executor or DirectCapabilityExecutor(db, current_user)
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.max_planner_failures = max_planner_failures
        self.max_repeated_identical_calls = max_repeated_identical_calls
        self.tool_timeout_seconds = tool_timeout_seconds

    def create_and_run(self, goal: str) -> AgentRunResponse:
        repository = AgentRunRepository(self.db, self.current_user.id)
        run = repository.create_run(goal)
        context = self._context(run.id)
        repository.add_event(run, "agent_run_started", 0, event_data(goal=goal))
        repository.set_status(run, "running")
        repository.commit()
        self._run_loop(run.id, context)
        return self._response(run.id)

    def get(self, run_id: str) -> AgentRunResponse:
        return self._response(run_id)

    def list(self) -> list[AgentRunResponse]:
        repository = AgentRunRepository(self.db, self.current_user.id)
        return [AgentRunResponse.model_validate(run) for run in repository.list_runs()]

    def cancel(self, run_id: str) -> AgentRunResponse:
        repository = AgentRunRepository(self.db, self.current_user.id)
        run = repository.get_run(run_id)
        if run is None:
            raise AgentRunNotFoundError
        if run.status in {"completed", "failed", "cancelled", "expired"}:
            return AgentRunResponse.model_validate(run)
        repository.set_status(run, "cancelled", cancelled_at=datetime.now(timezone.utc))
        repository.add_event(run, "agent_cancelled", run.current_iteration, {})
        repository.commit()
        return self._response(run_id)

    def approve(self, run_id: str, approved: bool) -> AgentRunResponse:
        repository = AgentRunRepository(self.db, self.current_user.id)
        run = repository.get_run(run_id)
        if run is None:
            raise AgentRunNotFoundError
        if run.status != "waiting_for_approval" or not run.pending_action:
            raise AgentRunStateError("run is not waiting for approval")
        if not approved:
            repository.set_status(
                run, "failed", failure_summary="user rejected the proposed action"
            )
            repository.add_event(
                run, "approval_received", run.current_iteration, {"approved": False}
            )
            repository.commit()
            return self._response(run_id)
        repository.set_status(run, "running", pending_action=None)
        repository.add_event(run, "approval_received", run.current_iteration, {"approved": True})
        repository.commit()
        self._run_loop(run_id, self._context(run_id))
        return self._response(run_id)

    def _run_loop(self, run_id: str, context: AgentExecutionContext) -> None:
        repository = AgentRunRepository(self.db, self.current_user.id)
        observations: list[dict[str, object]] = []
        completed_tools: list[str] = []
        while True:
            run = repository.get_run(run_id)
            if run is None:
                raise AgentRunNotFoundError
            if run.status == "cancelled":
                return
            if run.status in {"completed", "failed", "expired"}:
                return
            if run.current_iteration >= context.budget.max_iterations:
                self._fail(repository, run, "maximum iterations exceeded")
                return
            run.current_iteration += 1
            run.planner_call_count += 1
            repository.commit()
            planner_state = PlannerState(
                goal=run.goal,
                iteration=run.current_iteration,
                tool_call_count=run.tool_call_count,
                observations=observations,
                completed_tools=completed_tools,
            )
            planner_started = monotonic()
            repository.add_event(
                run,
                "planner_started",
                run.current_iteration,
                self._planner_metadata(),
            )
            repository.commit()
            try:
                decision = self.planner.decide(
                    run.goal,
                    planner_state,
                    self.executor.catalogue(set(self.allowed_capabilities)),
                )
                decision = PlanDecision.model_validate(decision)
                repository.add_event(
                    run,
                    "planner_completed",
                    run.current_iteration,
                    {
                        **self._planner_metadata(),
                        "duration_ms": int((monotonic() - planner_started) * 1000),
                        "decision": decision.decision,
                    },
                )
            except Exception:
                context.budget.planner_failures += 1
                repository.add_event(
                    run,
                    "planner_failed",
                    run.current_iteration,
                    {
                        **self._planner_metadata(),
                        "duration_ms": int((monotonic() - planner_started) * 1000),
                        "category": "planner_error",
                    },
                )
                if context.budget.planner_failures > context.budget.max_planner_failures:
                    self._fail(repository, run, "planner failed repeatedly")
                    return
                repository.commit()
                continue
            if decision.decision == "call_tool":
                if not decision.tool or decision.tool not in self.allowed_capabilities:
                    self._fail(repository, run, "planner selected an unavailable capability")
                    return
                if run.tool_call_count >= context.budget.max_tool_calls:
                    self._fail(repository, run, "maximum tool calls exceeded")
                    return
                call_key = self._call_key(decision.tool, decision.arguments)
                context.budget.repeated_calls[call_key] = (
                    context.budget.repeated_calls.get(call_key, 0) + 1
                )
                if (
                    context.budget.repeated_calls[call_key]
                    > context.budget.max_repeated_identical_calls
                ):
                    self._fail(repository, run, "repeated identical tool call limit exceeded")
                    return
                try:
                    step = repository.add_step(run, decision.tool, decision.arguments)
                    tool_call = repository.add_tool_call(step, decision.tool, decision.arguments)
                    repository.add_event(
                        run, "tool_selected", run.current_iteration, event_data(tool=decision.tool)
                    )
                    repository.commit()
                    if context.cancelled:
                        self.cancel(run_id)
                        return
                    started = monotonic()
                    result = self.executor.execute(decision.tool, decision.arguments, context)
                    duration_ms = int((monotonic() - started) * 1000)
                    if monotonic() - started > self.tool_timeout_seconds:
                        raise TimeoutError("capability execution exceeded its deadline")
                    observation = completed_observation(decision.tool, result, duration_ms)
                    tool_call.status = "completed"
                    tool_call.result = observation.result
                    step.status = "completed"
                    step.result_reference = tool_call.id
                    run.tool_call_count += 1
                except Exception as error:
                    observation = failed_observation(
                        decision.tool,
                        self._error_category(error),
                        (
                            "capability execution timed out"
                            if isinstance(error, TimeoutError)
                            else "capability execution failed"
                        ),
                        int((monotonic() - started) * 1000) if "started" in locals() else 0,
                    )
                    tool_call.status = "failed"
                    tool_call.error = observation.error.model_dump()
                    step.status = "failed"
                    run.tool_call_count += 1
                repository.add_observation(tool_call, observation.model_dump(mode="json"))
                repository.add_event(
                    run,
                    "tool_completed" if observation.status == "completed" else "tool_failed",
                    run.current_iteration,
                    event_data(tool=decision.tool),
                )
                repository.add_event(
                    run, "observation_received", run.current_iteration, {"tool": decision.tool}
                )
                repository.commit()
                observations.append(observation.model_dump(mode="json"))
                if observation.status == "completed":
                    completed_tools.append(decision.tool)
                continue
            if decision.decision == "complete":
                if not decision.summary or not any(
                    observation.get("status") == "completed" for observation in observations
                ):
                    self._fail(repository, run, "completion requires a summary and an observation")
                    return
                repository.set_status(
                    run,
                    "completed",
                    completion_summary=decision.summary,
                    completed_at=datetime.now(timezone.utc),
                )
                repository.add_event(
                    run, "agent_completed", run.current_iteration, {"summary": decision.summary}
                )
                repository.commit()
                return
            if decision.decision == "ask_user":
                repository.set_status(run, "waiting_for_user")
                repository.add_event(
                    run,
                    "user_input_requested",
                    run.current_iteration,
                    {"question": decision.question or "clarification required"},
                )
                repository.commit()
                return
            if decision.decision == "request_approval":
                repository.set_status(
                    run, "waiting_for_approval", pending_action=decision.model_dump(mode="json")
                )
                repository.add_event(
                    run, "approval_requested", run.current_iteration, {"tool": decision.tool}
                )
                repository.commit()
                return
            if decision.decision == "replan":
                run.plan_version += 1
                repository.add_event(run, "replan_started", run.current_iteration, {})
                repository.commit()
                continue
            self._fail(repository, run, decision.summary or "planner requested failure")
            return

    def _response(self, run_id: str) -> AgentRunResponse:
        repository = AgentRunRepository(self.db, self.current_user.id)
        run = repository.get_run(run_id)
        if run is None:
            raise AgentRunNotFoundError
        return AgentRunResponse.model_validate(run)

    def _context(self, run_id: str) -> AgentExecutionContext:
        return AgentExecutionContext(
            run_id=run_id,
            user_id=self.current_user.id,
            current_user=self.current_user,
            correlation_id=str(uuid4()),
            budget=BudgetState(
                max_iterations=self.max_iterations,
                max_tool_calls=self.max_tool_calls,
                max_planner_failures=self.max_planner_failures,
                max_repeated_identical_calls=self.max_repeated_identical_calls,
            ),
        )

    def _fail(self, repository: AgentRunRepository, run, summary: str) -> None:
        repository.set_status(run, "failed", failure_summary=summary)
        repository.add_event(run, "agent_failed", run.current_iteration, {"summary": summary})
        repository.commit()

    def _planner_metadata(self) -> dict[str, object]:
        return {
            "provider": getattr(self.planner, "provider_name", type(self.planner).__name__),
            "model": getattr(self.planner, "model", ""),
        }

    @staticmethod
    def _call_key(tool: str, arguments: dict[str, object]) -> str:
        payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(f"{tool}:{payload}".encode()).hexdigest()

    @staticmethod
    def _error_category(error: Exception) -> str:
        name = type(error).__name__.lower()
        if isinstance(error, ValidationError):
            return "validation_error"
        if "notfound" in name or "not_found" in name:
            return "not_found"
        if "provider" in name:
            return "provider_unavailable"
        return "execution_error"

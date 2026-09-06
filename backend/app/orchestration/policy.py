from __future__ import annotations

from app.orchestration.registry import CapabilityDefinition


class ExecutionPolicyError(ValueError):
    """Raised when a capability is outside the orchestrator policy."""


class ReadOnlyExecutionPolicy:
    max_capability_executions = 1
    max_depth = 0

    def authorize(self, capability: CapabilityDefinition) -> None:
        if capability.access_mode != "read_only":
            raise ExecutionPolicyError("capability is not read-only")
        if capability.risk_level != "low":
            raise ExecutionPolicyError("capability risk is not permitted")

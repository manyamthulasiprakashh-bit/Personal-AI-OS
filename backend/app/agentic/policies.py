from __future__ import annotations

from app.orchestration.policy import ExecutionPolicyError
from app.orchestration.registry import CapabilityDefinition


class AgenticExecutionPolicy:
    """Policy for the model-facing, read-only capability surface."""

    def authorize(self, capability: CapabilityDefinition) -> None:
        if capability.access_mode != "read_only":
            raise ExecutionPolicyError("capability is not read-only")
        if capability.risk_level != "low":
            raise ExecutionPolicyError("capability risk is not permitted")

    def requires_approval(self, capability: CapabilityDefinition) -> bool:
        return capability.access_mode != "read_only"

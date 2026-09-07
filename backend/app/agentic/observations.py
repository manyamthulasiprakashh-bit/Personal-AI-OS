from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ObservationStatus = Literal["completed", "failed"]


class ObservationError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    message: str = Field(max_length=500)


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    status: ObservationStatus
    result: dict[str, Any] | None = None
    error: ObservationError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _bound(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "[truncated]"
    if isinstance(value, str):
        return value[:4000]
    if isinstance(value, list):
        return [_bound(item, depth + 1) for item in value[:50]]
    if isinstance(value, dict):
        return {str(key): _bound(item, depth + 1) for key, item in list(value.items())[:50]}
    return value


def completed_observation(tool: str, result: Any, duration_ms: int) -> Observation:
    payload = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
    return Observation(
        tool=tool,
        status="completed",
        result=_bound(payload),
        metadata={"duration_ms": duration_ms, "source": "capability"},
    )


def failed_observation(tool: str, category: str, message: str, duration_ms: int) -> Observation:
    return Observation(
        tool=tool,
        status="failed",
        error=ObservationError(category=category, message=message[:500]),
        metadata={"duration_ms": duration_ms, "source": "capability"},
    )

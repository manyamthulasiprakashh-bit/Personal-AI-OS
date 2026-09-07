from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.providers.factory import get_agent_planner_provider
from app.agentic.planner import PlannerProvider
from app.schemas.agentic import AgentApprovalRequest, AgentRunCreate, AgentRunResponse
from app.services.agentic_service import (
    AgentRunNotFoundError,
    AgentRunStateError,
    AgenticRuntimeService,
)

router = APIRouter(prefix="/api/agent/runs", tags=["agentic"])


def get_agentic_service(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    planner: PlannerProvider = Depends(get_agent_planner_provider),
) -> AgenticRuntimeService:
    return AgenticRuntimeService(db, current_user, planner=planner)


@router.post("", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
def create_agent_run(
    payload: AgentRunCreate,
    service: AgenticRuntimeService = Depends(get_agentic_service),
) -> AgentRunResponse:
    return service.create_and_run(payload.goal)


@router.get("", response_model=list[AgentRunResponse])
def list_agent_runs(
    service: AgenticRuntimeService = Depends(get_agentic_service),
) -> list[AgentRunResponse]:
    return service.list()


@router.get("/{run_id}", response_model=AgentRunResponse)
def get_agent_run(
    run_id: str, service: AgenticRuntimeService = Depends(get_agentic_service)
) -> AgentRunResponse:
    try:
        return service.get(run_id)
    except AgentRunNotFoundError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error


@router.post("/{run_id}/cancel", response_model=AgentRunResponse)
def cancel_agent_run(
    run_id: str, service: AgenticRuntimeService = Depends(get_agentic_service)
) -> AgentRunResponse:
    try:
        return service.cancel(run_id)
    except AgentRunNotFoundError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error


@router.post("/{run_id}/approve", response_model=AgentRunResponse)
def approve_agent_run(
    run_id: str,
    payload: AgentApprovalRequest,
    service: AgenticRuntimeService = Depends(get_agentic_service),
) -> AgentRunResponse:
    try:
        return service.approve(run_id, payload.approved)
    except AgentRunNotFoundError as error:
        raise HTTPException(status_code=404, detail="agent run not found") from error
    except AgentRunStateError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

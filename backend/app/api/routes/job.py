from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.agents.job.agent import JobAnalysisAgent, JobProviderError
from app.database.session import get_db
from app.providers.factory import get_job_provider
from app.providers.job import JobProvider
from app.schemas.job import (
    JobAnalysisRequest,
    JobAnalysisResponse,
    JobOpportunityCreate,
    JobOpportunityResponse,
    JobOpportunityUpdate,
)
from app.services.job_service import JobNotFoundError, JobService, JobValidationError

router = APIRouter(prefix="/api", tags=["jobs"])


def get_job_service(
    db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
) -> JobService:
    return JobService(db, current_user.id)


def get_job_analysis_agent(
    service: JobService = Depends(get_job_service),
    provider: JobProvider = Depends(get_job_provider),
) -> JobAnalysisAgent:
    return JobAnalysisAgent(service, provider)


def _not_found(error: JobNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job opportunity not found")


def _validation(error: JobValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/jobs", response_model=JobOpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobOpportunityCreate, service: JobService = Depends(get_job_service)
) -> JobOpportunityResponse:
    return JobOpportunityResponse.model_validate(service.create(payload))


@router.get("/jobs", response_model=list[JobOpportunityResponse])
def list_jobs(service: JobService = Depends(get_job_service)) -> list[JobOpportunityResponse]:
    return [JobOpportunityResponse.model_validate(job) for job in service.list()]


@router.get("/jobs/{job_id}", response_model=JobOpportunityResponse)
def get_job(job_id: str, service: JobService = Depends(get_job_service)) -> JobOpportunityResponse:
    try:
        return JobOpportunityResponse.model_validate(service.get(job_id))
    except JobNotFoundError as error:
        raise _not_found(error) from error


@router.patch("/jobs/{job_id}", response_model=JobOpportunityResponse)
def update_job(
    job_id: str,
    payload: JobOpportunityUpdate,
    service: JobService = Depends(get_job_service),
) -> JobOpportunityResponse:
    try:
        return JobOpportunityResponse.model_validate(service.update(job_id, payload))
    except JobNotFoundError as error:
        raise _not_found(error) from error
    except JobValidationError as error:
        raise _validation(error) from error


@router.post("/jobs/{job_id}/archive", response_model=JobOpportunityResponse)
def archive_job(
    job_id: str, service: JobService = Depends(get_job_service)
) -> JobOpportunityResponse:
    try:
        return JobOpportunityResponse.model_validate(service.archive(job_id))
    except JobNotFoundError as error:
        raise _not_found(error) from error


@router.post("/jobs/{job_id}/agent/analyze", response_model=JobAnalysisResponse)
def analyze_job(
    job_id: str,
    payload: JobAnalysisRequest,
    agent: JobAnalysisAgent = Depends(get_job_analysis_agent),
) -> JobAnalysisResponse:
    try:
        return agent.analyze(job_id)
    except JobNotFoundError as error:
        raise _not_found(error) from error
    except JobProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="job analysis is unavailable",
        ) from error

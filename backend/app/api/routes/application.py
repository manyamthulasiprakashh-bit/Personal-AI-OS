from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.repositories.application import ApplicationConflictError
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from app.services.application_service import (
    ApplicationJobNotFoundError,
    ApplicationNotFoundError,
    ApplicationService,
    ApplicationValidationError,
)

router = APIRouter(prefix="/api", tags=["applications"])


def get_application_service(
    db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
) -> ApplicationService:
    return ApplicationService(db, current_user.id)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    payload: ApplicationCreate,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    try:
        return ApplicationResponse.model_validate(service.create(payload))
    except ApplicationJobNotFoundError as error:
        raise _not_found("job opportunity not found") from error
    except ApplicationConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an active application already exists for this job",
        ) from error
    except ApplicationValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    service: ApplicationService = Depends(get_application_service),
) -> list[ApplicationResponse]:
    return [ApplicationResponse.model_validate(application) for application in service.list()]


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    try:
        return ApplicationResponse.model_validate(service.get(application_id))
    except ApplicationNotFoundError as error:
        raise _not_found("application not found") from error


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    try:
        return ApplicationResponse.model_validate(service.update(application_id, payload))
    except ApplicationNotFoundError as error:
        raise _not_found("application not found") from error
    except ApplicationConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="an active application already exists for this job",
        ) from error
    except ApplicationValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

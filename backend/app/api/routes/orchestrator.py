from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.job.agent import JobProviderError
from app.agents.learning.agent import LearningProviderError
from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.providers.factory import get_job_provider, get_learning_provider, get_stock_provider
from app.providers.job import JobProvider
from app.providers.learning import LearningProvider
from app.providers.stock import StockProvider, StockProviderError, StockQuoteNotFoundError
from app.schemas.orchestrator import OrchestratorRequest, OrchestratorResponse
from app.services.job_service import JobNotFoundError
from app.services.orchestrator_service import (
    AmbiguousIntentError,
    MissingCapabilityArgumentError,
    OrchestratorService,
    OrchestratorError,
    UnknownIntentError,
    UnsupportedCapabilityError,
)

router = APIRouter(prefix="/api", tags=["orchestrator"])


def get_orchestrator_service(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    learning_provider: LearningProvider = Depends(get_learning_provider),
    job_provider: JobProvider = Depends(get_job_provider),
    stock_provider: StockProvider = Depends(get_stock_provider),
) -> OrchestratorService:
    return OrchestratorService(
        db,
        current_user,
        learning_provider=learning_provider,
        job_provider=job_provider,
        stock_provider=stock_provider,
    )


@router.post("/orchestrator/run", response_model=OrchestratorResponse)
def run_orchestrator(
    payload: OrchestratorRequest,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> OrchestratorResponse:
    try:
        return service.run(payload.message)
    except (UnknownIntentError, AmbiguousIntentError, MissingCapabilityArgumentError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except UnsupportedCapabilityError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unsupported capability",
        ) from error
    except HTTPException:
        raise
    except JobNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job opportunity not found"
        ) from error
    except StockQuoteNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="stock quote not found"
        ) from error
    except (LearningProviderError, JobProviderError, StockProviderError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="orchestrated capability is unavailable",
        ) from error
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="orchestrated capability is unavailable",
        ) from error
    except OrchestratorError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="orchestration failed",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="orchestration failed",
        ) from error

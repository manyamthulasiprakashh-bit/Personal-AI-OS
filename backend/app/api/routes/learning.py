from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.learning.agent import LearningAgent, LearningProviderError
from app.api.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.providers.factory import get_learning_provider
from app.providers.learning import LearningProvider
from app.schemas.learning import LearningAgentResponse, LearningRecommendationRequest
from app.services.learning_service import LearningService

router = APIRouter(prefix="/api", tags=["learning"])


def get_learning_service(
    db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
) -> LearningService:
    return LearningService(db, current_user.id)


def get_learning_agent(
    service: LearningService = Depends(get_learning_service),
    provider: LearningProvider = Depends(get_learning_provider),
) -> LearningAgent:
    return LearningAgent(service, provider)


@router.post("/learning/agent/recommend", response_model=LearningAgentResponse)
def recommend_learning(
    payload: LearningRecommendationRequest,
    agent: LearningAgent = Depends(get_learning_agent),
) -> LearningAgentResponse:
    try:
        return agent.recommend(payload.goal_id)
    except LearningProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="learning recommendation is unavailable",
        ) from error

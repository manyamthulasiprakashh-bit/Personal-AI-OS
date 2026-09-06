from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.learning import LearningRepository
from app.schemas.learning import (
    LearningGoalCreate,
    LearningProgress,
    LearningResourceCreate,
    LearningSessionCreate,
)
from app.models.learning import LearningSession


class LearningService:
    def __init__(self, db: Session, user_id: str):
        self.repository = LearningRepository(db, user_id)

    def create_goal(self, payload: LearningGoalCreate):
        return self.repository.create_goal(payload.model_dump())

    def list_goals(self):
        return self.repository.list_goals()

    def get_goal(self, goal_id: str):
        goal = self.repository.get_goal(goal_id)
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="learning goal not found"
            )
        return goal

    def create_session(self, payload: LearningSessionCreate) -> LearningSession:
        self.get_goal(payload.goal_id)
        return self.repository.create_session(payload.model_dump())

    def list_sessions(self, goal_id: str | None = None) -> list[LearningSession]:
        if goal_id is not None:
            self.get_goal(goal_id)
        return self.repository.list_sessions(goal_id)

    def create_resource(self, payload: LearningResourceCreate):
        if payload.goal_id is not None:
            self.get_goal(payload.goal_id)
        return self.repository.create_resource(payload.model_dump())

    def get_progress(self, goal_id: str | None = None) -> LearningProgress:
        if goal_id is not None:
            self.get_goal(goal_id)
        return LearningProgress(**self.repository.get_progress(goal_id))

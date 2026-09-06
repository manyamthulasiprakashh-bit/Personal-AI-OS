from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.learning import LearningGoal, LearningResource, LearningSession


class LearningRepository:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def create_goal(self, payload: dict[str, Any]) -> LearningGoal:
        goal = LearningGoal(user_id=self.user_id, **payload)
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def list_goals(self) -> list[LearningGoal]:
        query = (
            select(LearningGoal)
            .where(LearningGoal.user_id == self.user_id)
            .order_by(LearningGoal.created_at.asc())
        )
        return list(self.db.execute(query).scalars().all())

    def get_goal(self, goal_id: str) -> LearningGoal | None:
        query = select(LearningGoal).where(
            LearningGoal.id == goal_id, LearningGoal.user_id == self.user_id
        )
        return self.db.execute(query).scalar_one_or_none()

    def create_session(self, payload: dict[str, Any]) -> LearningSession:
        session = LearningSession(user_id=self.user_id, **payload)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def create_resource(self, payload: dict[str, Any]) -> LearningResource:
        resource = LearningResource(user_id=self.user_id, **payload)
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def get_progress(self, goal_id: str | None = None) -> dict[str, int | str | None]:
        goal_query = select(LearningGoal).where(LearningGoal.user_id == self.user_id)
        session_query = select(
            func.count(LearningSession.id),
            func.coalesce(func.sum(LearningSession.duration_minutes), 0),
        ).where(LearningSession.user_id == self.user_id)
        if goal_id is not None:
            goal_query = goal_query.where(LearningGoal.id == goal_id)
            session_query = session_query.where(LearningSession.goal_id == goal_id)

        goals = list(self.db.execute(goal_query).scalars().all())
        session_count, total_minutes = self.db.execute(session_query).one()
        return {
            "goal_id": goal_id,
            "total_goals": len(goals),
            "active_goals": sum(1 for goal in goals if goal.status == "active"),
            "completed_goals": sum(1 for goal in goals if goal.status == "completed"),
            "total_sessions": int(session_count or 0),
            "total_minutes": int(total_minutes or 0),
        }

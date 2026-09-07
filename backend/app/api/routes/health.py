from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "service": "personal-ai-os-backend",
                "database": "unavailable",
            },
        )
    return {"status": "ok", "service": "personal-ai-os-backend", "database": "ok"}


@router.get("/dashboard")
async def dashboard() -> dict[str, object]:
    return {
        "today": {
            "tasks_completed": 0,
            "study_time_hours": 0,
            "job_applications": 0,
            "learning_progress": 0,
            "ai_recommendations": [],
        },
        "agent_activity": [
            {"agent": "Routine Agent", "status": "idle"},
            {"agent": "Learning Agent", "status": "idle"},
            {"agent": "Job Agent", "status": "idle"},
            {"agent": "Stock Agent", "status": "idle"},
        ],
    }

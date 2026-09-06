from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "personal-ai-os-backend"}


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

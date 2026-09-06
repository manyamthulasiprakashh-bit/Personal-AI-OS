from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.routine import router as routine_router
from app.config import get_settings
from app.database.session import init_db
from app.utils.logging import configure_logging

configure_logging()
settings = get_settings()
init_db()

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Personal AI Operating System backend foundation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(routine_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": settings.project_name}

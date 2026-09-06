from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.agents.routine.agent import RoutineAgent
from app.database.session import get_db
from app.providers.factory import get_provider
from app.schemas.routine import (
    AgentReviewInput,
    AgentReviewResponse,
    ActivityCreate,
    ActivityResponse,
    DailyPlanResponse,
    DailyProgressResponse,
    DailyReviewInput,
    DailyReviewResponse,
    HabitCreate,
    HabitLogCreate,
    HabitLogResponse,
    HabitResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.routine_service import RoutineService

router = APIRouter(prefix="/api", tags=["routine"])


def get_routine_service(db: Session = Depends(get_db)) -> RoutineService:
    return RoutineService(db)


def get_routine_agent() -> RoutineAgent:
    return RoutineAgent(provider=get_provider())


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate, service: RoutineService = Depends(get_routine_service)
) -> TaskResponse:
    task = service.create_task(payload.model_dump())
    return TaskResponse.model_validate(task)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    planned_date: date | None = Query(default=None),
    service: RoutineService = Depends(get_routine_service),
) -> list[TaskResponse]:
    tasks = service.list_tasks(planned_date=planned_date)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, service: RoutineService = Depends(get_routine_service)) -> TaskResponse:
    task = service.get_task(task_id)
    return TaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str, payload: TaskUpdate, service: RoutineService = Depends(get_routine_service)
) -> TaskResponse:
    task = service.update_task(task_id, payload.model_dump(exclude_none=True))
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: str, service: RoutineService = Depends(get_routine_service)
) -> TaskResponse:
    task = service.complete_task(task_id)
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/skip", response_model=TaskResponse)
def skip_task(task_id: str, service: RoutineService = Depends(get_routine_service)) -> TaskResponse:
    task = service.skip_task(task_id)
    return TaskResponse.model_validate(task)


@router.post("/habits", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    payload: HabitCreate, service: RoutineService = Depends(get_routine_service)
) -> HabitResponse:
    habit = service.create_habit(payload.model_dump())
    return HabitResponse.model_validate(habit)


@router.get("/habits", response_model=list[HabitResponse])
def list_habits(service: RoutineService = Depends(get_routine_service)) -> list[HabitResponse]:
    habits = service.list_habits()
    return [HabitResponse.model_validate(habit) for habit in habits]


@router.post(
    "/habits/{habit_id}/log", response_model=HabitLogResponse, status_code=status.HTTP_201_CREATED
)
def log_habit(
    habit_id: str, payload: HabitLogCreate, service: RoutineService = Depends(get_routine_service)
) -> HabitLogResponse:
    habit_log = service.log_habit(habit_id, payload.model_dump())
    return HabitLogResponse.model_validate(habit_log)


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate, service: RoutineService = Depends(get_routine_service)
) -> ActivityResponse:
    activity = service.log_activity(payload.model_dump())
    return ActivityResponse.model_validate(activity)


@router.get("/activities", response_model=list[ActivityResponse])
def list_activities(
    planned_date: date | None = Query(default=None),
    service: RoutineService = Depends(get_routine_service),
) -> list[ActivityResponse]:
    activities = service.list_activities(planned_date=planned_date)
    return [ActivityResponse.model_validate(activity) for activity in activities]


@router.get("/routine/today", response_model=DailyPlanResponse)
def today_plan(service: RoutineService = Depends(get_routine_service)) -> DailyPlanResponse:
    plan = service.get_daily_plan(date.today())
    return DailyPlanResponse(
        date=plan["date"],
        tasks=[TaskResponse.model_validate(task) for task in plan["tasks"]],
        habits=[HabitResponse.model_validate(habit) for habit in plan["habits"]],
        total_planned_minutes=plan["total_planned_minutes"],
    )


@router.get("/routine/progress", response_model=DailyProgressResponse)
def daily_progress(
    target_date: date = Query(default_factory=date.today),
    service: RoutineService = Depends(get_routine_service),
) -> DailyProgressResponse:
    progress = service.calculate_daily_progress(target_date)
    return DailyProgressResponse(**progress)


@router.post("/routine/review", response_model=DailyReviewResponse)
def create_review(
    payload: DailyReviewInput,
    service: RoutineService = Depends(get_routine_service),
) -> DailyReviewResponse:
    review = service.generate_daily_review(payload.date)
    return DailyReviewResponse.model_validate(review)


@router.post("/routine/agent/review", response_model=AgentReviewResponse)
def agent_review(
    payload: AgentReviewInput,
    agent: RoutineAgent = Depends(get_routine_agent),
) -> AgentReviewResponse:
    result = agent.review_day(payload.date)
    return AgentReviewResponse(**result)

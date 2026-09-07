from __future__ import annotations

from uuid import uuid4

from app.api.dependencies import CurrentUser
from app.database.session import SessionLocal
from app.models.user import User
from app.providers.factory import get_agent_planner_provider
from app.services.agentic_service import AgenticRuntimeService


def main() -> None:
    planner = get_agent_planner_provider()
    if getattr(planner, "provider_name", "") != "local":
        raise RuntimeError("set AGENT_PLANNER_PROVIDER=local for this verification")

    db = SessionLocal()
    user = User(email=f"local-planner-{uuid4()}@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    try:
        run = AgenticRuntimeService(
            db=db,
            current_user=CurrentUser(user.id, user.email),
            planner=planner,
        ).create_and_run("Help me understand what I need to become an AI Engineer.")
        print(f"provider: {planner.provider_name}")
        print(f"model: {planner.model}")
        print(f"run_id: {run.id}")
        print(f"status: {run.status}")
        print(f"planner_call_count: {run.planner_call_count}")
        print(f"tool_call_count: {run.tool_call_count}")
        print(
            "event_types:",
            [event.event_type for event in run.events],
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

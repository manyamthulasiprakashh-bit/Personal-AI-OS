# Architecture Overview

## Core principles

- Keep the user as the final decision-maker for all sensitive actions.
- Separate orchestration, agents, shared memory, and provider abstractions.
- Favor explicit interfaces and clean boundaries over hidden coupling.
- Keep security and auditability as first-class concerns.

## Implemented phases

The repository implements Phase 1 responsibilities and Phase 2B of the Daily Routine Agent MVP:

- FastAPI app shell with health and dashboard endpoints
- PostgreSQL / SQLAlchemy configuration
- Alembic migrations for routine models
- Basic Next.js dashboard shell
- Structured logging and environment configuration
- `RoutineAgent.review_day()` execution through the allowlisted `get_daily_progress` tool
- Deterministic daily progress calculation
- `BaseProvider` with `MockProvider` as the default provider
- `POST /api/routine/agent/review` returning progress and a structured review

## Local Phase 2B flow

Local development requires PostgreSQL at `localhost:5432` with the database, user, and password configured by `.env` from `.env.example`:

- Database: `personal_ai_os`
- User: `personal_ai_os`
- Password: `personal_ai_os`

Apply the existing migration and start the backend with:

```bash
make alembic-upgrade
make backend-run
```

The Phase 2B endpoint accepts `{"date":"YYYY-MM-DD"}` at `POST /api/routine/agent/review`. Its response contains deterministic `progress` and a structured `review` with `summary`, `observations`, `recommendations`, and `tomorrow_priorities`.

Example smoke test:

```bash
curl -X POST http://localhost:8000/api/routine/agent/review \
	-H "Content-Type: application/json" \
	-d '{"date":"2026-09-06"}'
```

## Planned architecture

- Orchestrator coordinates agent execution and approval requests.
- Agents expose tool-based interfaces and operate on the shared memory layer.
- Shared memory persists user, job, learning, and market data in PostgreSQL.
- The LLM provider abstraction allows provider changes without affecting business logic.
- Dashboard reads aggregated state from backend APIs.

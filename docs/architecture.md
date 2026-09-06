# Architecture Overview

## Core principles

- Keep the user as the final decision-maker for all sensitive actions.
- Separate orchestration, agents, shared memory, and provider abstractions.
- Favor explicit interfaces and clean boundaries over hidden coupling.
- Keep security and auditability as first-class concerns.

## Implemented phases

The repository implements Phase 1, Phase 2B of the Daily Routine Agent MVP, Phase 3A, Phase 3B, and Phase 3C:

- FastAPI app shell with health and dashboard endpoints
- PostgreSQL / SQLAlchemy configuration
- Alembic migrations for routine models
- Basic Next.js dashboard shell
- Structured logging and environment configuration
- `RoutineAgent.review_day()` execution through the allowlisted `get_daily_progress` tool
- Deterministic daily progress calculation
- `BaseProvider` with `MockProvider` as the default provider
- `POST /api/routine/agent/review` returning progress and a structured review
- Phase 3A learning models, migration, typed schemas, owner-scoped repository, and deterministic service
- Configured active development-user boundary through `get_current_user()`
- Phase 3B `LearningAgent` read-only recommendation workflow
- `POST /api/learning/agent/recommend` returning deterministic progress and a typed recommendation
- Phase 3C owner-scoped learning session creation and history retrieval
- `POST /api/learning/sessions` and `GET /api/learning/sessions`

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

## Local Phase 3B flow

The Learning Agent uses the configured active development user from `DEVELOPMENT_USER_EMAIL`. The user must exist and be active in PostgreSQL. This is a development identity boundary, not production authentication.

The recommendation workflow is:

```text
API -> current-user dependency -> LearningAgent -> allowlisted get_learning_progress tool
-> deterministic LearningService -> LearningRepository -> LearningProgress
-> LearningProvider -> LearningRecommendation -> API response
```

The endpoint is:

```text
POST /api/learning/agent/recommend
```

It accepts an optional `goal_id`:

```json
{}
```

or:

```json
{"goal_id": "<owned-learning-goal-id>"}
```

The response contains `progress` and a typed `recommendation` with `summary`, `observations`, `recommendations`, and `next_steps`. Empty learning data returns deterministic zero progress and a stable MockProvider recommendation. Provider failures return `503 Service Unavailable`.

Phase 3B is recommendation-only. It does not add recommendation persistence, real LLM providers, external research, file ingestion, scheduling, notifications, or production authentication.

## Local Phase 3C flow

Learning sessions use the configured current development user and existing Phase 3A ownership boundary:

```text
API -> current-user dependency -> LearningService(user_id)
-> owner-scoped LearningRepository -> LearningSession persistence/query
-> typed response
```

The session endpoints are:

```text
POST /api/learning/sessions
GET  /api/learning/sessions
GET  /api/learning/sessions?goal_id=<owned-goal-id>
```

Session creation validates the owned goal, duration, timestamp order, and rejects unknown request fields. Listing returns only the current user's sessions; a goal filter remains owner-scoped. New session minutes are included in deterministic learning progress and therefore in later recommendations.

The Learning Agent remains read-only. Phase 3C does not add agent write tools, scheduling, notifications, external research, resource ingestion, recommendation persistence, or production authentication.

## Planned architecture

- Orchestrator coordinates agent execution and approval requests.
- Agents expose tool-based interfaces and operate on the shared memory layer.
- Shared memory persists user, job, learning, and market data in PostgreSQL.
- The LLM provider abstraction allows provider changes without affecting business logic.
- Dashboard reads aggregated state from backend APIs.

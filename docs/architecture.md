# Architecture Overview

## Core principles

- Keep the user as the final decision-maker for all sensitive actions.
- Separate orchestration, agents, shared memory, and provider abstractions.
- Favor explicit interfaces and clean boundaries over hidden coupling.
- Keep security and auditability as first-class concerns.

## Implemented phases

The repository implements Phase 1, Phase 2B of the Daily Routine Agent MVP, Phase 3A, Phase 3B, Phase 3C, Phase 3D, and Phase 4A:

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
- Phase 3D owner-scoped learning goal creation, listing, and retrieval
- `POST /api/learning/goals`, `GET /api/learning/goals`, and `GET /api/learning/goals/{goal_id}`
- Phase 4A owner-scoped manual job opportunity tracking
- `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{job_id}`, `PATCH /api/jobs/{job_id}`, and `POST /api/jobs/{job_id}/archive`
 - Phase 4B read-only Job Analysis Agent over existing owned opportunities

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

## Local Phase 3D flow

The Learning MVP now begins through the public API:

```text
API -> current-user dependency -> LearningService(user_id)
-> owner-scoped LearningRepository -> LearningGoal persistence/query
-> typed response
```

The goal endpoints are:

```text
POST /api/learning/goals
GET  /api/learning/goals
GET  /api/learning/goals/{goal_id}
```

Goal creation rejects unknown fields and client-supplied ownership fields. Listing and retrieval return only goals belonging to the current development user; another user's goal behaves as not found. Created goals appear in `GET /api/learning/progress` and can be used with the existing session endpoints. Goal update and deletion are not implemented.

## Local Phase 4A flow

Phase 4A is a persistence and API foundation for manually saved job opportunities:

```text
API -> current-user dependency -> JobService(user_id)
-> owner-scoped JobRepository -> JobOpportunity persistence/query
-> typed response
```

The job endpoints are:

```text
POST  /api/jobs
GET   /api/jobs
GET   /api/jobs/{job_id}
PATCH /api/jobs/{job_id}
POST  /api/jobs/{job_id}/archive
```

Users provide the opportunity metadata and optional `description_snapshot`. The URL is inert reference data; the backend does not fetch, scrape, or crawl it. Records are owner-scoped, and cross-user access behaves as not found. Status transitions support saved to reviewing and explicit archive; archived records are terminal in Phase 4A.

Phase 4A does not include a JobAgent, job tools, applications, resumes, interviews, external discovery, network calls, notifications, scheduling, or real LLM providers.

## Local Phase 4B flow

The Job Analysis Agent reads one owner-scoped opportunity and returns transient typed analysis:

```text
API -> current-user dependency -> JobService(user_id) -> JobAnalysisAgent
-> allowlisted get_job_analysis_input -> JobAnalysisInput
-> JobProvider -> JobAnalysis -> API response
```

The endpoint is:

```text
POST /api/jobs/{job_id}/agent/analyze
```

It accepts `{}` only. The single tool is read-only, and the deterministic `MockJobProvider` receives only the typed job input. Analysis does not access Routine or Learning data, fetch the inert job URL, make external network calls, persist results, or mutate job fields.

Phase 4B excludes real LLM providers, job discovery, scraping, applications, resumes, interviews, scheduling, notifications, email, employer contact, and autonomous writes.
## Planned architecture

- Orchestrator coordinates agent execution and approval requests.
- Agents expose tool-based interfaces and operate on the shared memory layer.
- Shared memory persists user, job, learning, and market data in PostgreSQL.
- The LLM provider abstraction allows provider changes without affecting business logic.
- Dashboard reads aggregated state from backend APIs.

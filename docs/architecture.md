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

## Local Phase 4C flow

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

It accepts `{}` only. The single tool is read-only. The default `MockJobProvider` receives only the typed job input and makes no network calls. With explicit `JOB_PROVIDER=llm`, `LLMJobProvider` sends one structured analysis request to the configured OpenAI Responses API. The request uses strict Pydantic output parsing, `store=False`, an explicit timeout, bounded input/output, and no model-controlled tools. Job description and notes are labeled as untrusted data and are never inserted into trusted instructions.

Provider selection is configuration-driven:

```text
JOB_PROVIDER=mock  -> MockJobProvider
JOB_PROVIDER=llm   -> LLMJobProvider
```

`OPENAI_API_KEY` is required only for explicit LLM mode. Missing configuration, connection failures, timeouts, authentication/rate-limit/status failures, refusals, incomplete responses, malformed output, and oversized input are converted to the existing provider failure path and exposed as `503 Service Unavailable`. No raw prompts, job text, provider responses, keys, or tokens are logged.

Phase 4C still excludes job discovery, scraping, crawling, URL fetching, application tracking, resumes, interviews, scheduling, notifications, email, employer contact, model tools, database migrations, persistence of analysis, and autonomous writes. No database schema changes are required.

## Local Phase 4D flow

Application Tracking is a deterministic, owner-scoped workflow separate from the JobOpportunity lifecycle:

```text
API -> current-user dependency -> ApplicationService(user_id)
-> owner-scoped ApplicationRepository -> Application persistence/query
-> typed response
```

The endpoints are:

```text
POST  /api/applications
GET   /api/applications
GET   /api/applications/{application_id}
PATCH /api/applications/{application_id}
```

An application belongs to one owned job opportunity and cannot be created for an archived job. The client cannot provide `user_id` or change `job_id`. Active duplicate applications for the same user and job are rejected. The application lifecycle is `applied -> interviewing -> offer`, with `rejected` and `withdrawn` as terminal outcomes; service-level validation enforces transitions. Existing applications remain viewable after their job is archived.

Phase 4D has no Application Agent, LLM calls, application event history, resume handling, email, external integrations, browser automation, or autonomous actions.

## Local Phase 5 flow

The Stock Quote MVP is a read-only, non-persistent provider workflow:

```text
GET /api/stocks/{symbol} -> StockService -> StockProvider -> StockQuote -> API response
```

Provider selection is configuration-driven:

```text
STOCK_PROVIDER=mock          -> MockStockProvider
STOCK_PROVIDER=alphavantage -> AlphaVantageStockProvider
```

The mock provider is the default and makes no network calls. The Alpha Vantage provider uses the configured official REST base URL, API key, `GLOBAL_QUOTE`, and an explicit timeout. Symbols are normalized and validated before provider invocation. Provider errors are sanitized into `404` or `503` responses; API keys, provider URLs, raw responses, and exception details are never returned.

The response is informational only and includes `market_data_status`. Alpha Vantage's default quote behavior is represented as `end_of_day`; the implementation does not claim realtime data. Phase 5 adds no SQLAlchemy model, repository, migration, database read/write, LLM, Stock Agent, tools, brokerage integration, trading, watchlist, or historical persistence.

## Local Phase 6 flow

Phase 6 adds a request-scoped, deterministic coordinator:

```text
POST /api/orchestrator/run -> CurrentUser -> OrchestratorService
	-> static CapabilityRegistry -> read-only ExecutionPolicy
	-> one approved capability -> validated typed response
```

The registry exposes only `learning.recommend`, `job.analyze`, and `stock.quote`. The orchestrator calls the existing LearningAgent, JobAnalysisAgent, or StockService; it does not duplicate domain logic or perform direct database queries. Provider selection remains inside existing provider factories.

Each request executes at most one capability with depth zero. Unknown, ambiguous, multi-action, or denied requests return validation errors. Existing service and repository ownership checks remain authoritative, and the request cannot provide `user_id`, provider names, tools, handlers, URLs, SQL, or filesystem operations.

The Phase 6 MVP is intentionally not an LLM planner. It has no database persistence, migrations, agent-to-agent calls, application writes, Routine exposure, trading, brokerage, notifications, browser automation, or arbitrary execution. Routine is excluded because its current records are global and its agent exposes write-capable tools; Application Tracking is excluded because it mutates state.
## Planned architecture

- Orchestrator coordinates agent execution and approval requests.
- Agents expose tool-based interfaces and operate on the shared memory layer.
- Shared memory persists user, job, learning, and market data in PostgreSQL.
- The LLM provider abstraction allows provider changes without affecting business logic.
- Dashboard reads aggregated state from backend APIs.

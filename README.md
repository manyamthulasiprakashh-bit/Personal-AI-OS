# Personal AI-OS

Personal AI-OS is a portfolio-grade monorepo for orchestrating personal productivity, learning, job search, and stock market analysis with a multi-agent architecture.

## Current status

Phase 1, Phase 2B, Phase 3A, Phase 3B, Phase 3D, and Phase 4A are complete. The repository currently contains:

- FastAPI backend foundation
- SQLAlchemy + PostgreSQL configuration
- Alembic migrations
- Basic Next.js frontend shell
- Health and dashboard endpoints
- Logging, env configuration, and tests
- RoutineAgent execution flow with deterministic daily progress
- MockProvider structured daily reviews
- `POST /api/routine/agent/review`
- User-owned learning data foundation
- Learning Agent read-only recommendation workflow
- `POST /api/learning/agent/recommend`
- Learning session logging and owner-scoped session history
- `POST /api/learning/sessions`
- `GET /api/learning/sessions`
- Owner-scoped Learning Goal creation, listing, and retrieval
- `POST /api/learning/goals`
- `GET /api/learning/goals`
- `GET /api/learning/goals/{goal_id}`
- Owner-scoped manual job opportunity tracking
- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `PATCH /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/archive`
 - Phase 4B read-only Job Analysis Agent
 - Phase 5 read-only Stock Quote API with mock and Alpha Vantage providers

## Development roadmap

1. Phase 1: Project foundation
2. Phase 2: Daily Routine Agent MVP (Phase 2B complete)
3. Phase 3: Learning Agent MVP (Phase 3A, Phase 3B, Phase 3C, and Phase 3D complete)
4. Phase 4: Job Application Agent MVP (Phase 4A manual job tracking complete)
5. Phase 5: Stock Market Agent MVP
6. Phase 6: Agent Orchestrator
7. Phase 7: Agent-to-agent workflows
8. Phase 8: Security hardening, authentication, testing, observability, deployment

## Repository structure

```text
personal-ai-os/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── config.py
│   │   ├── database/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/
├── infrastructure/
├── docs/
├── scripts/
├── .env.example
├── Makefile
├── README.md
└── .gitignore
```

## Local development

The backend requires a local PostgreSQL server. The default configuration expects:

- Database: `personal_ai_os`
- User: `personal_ai_os`
- Password: `personal_ai_os`
- Host: `localhost`
- Port: `5432`

Copy the environment template and ensure PostgreSQL is running before applying the migration:

```bash
cp .env.example .env
make backend-install
make alembic-upgrade
make backend-run
```

Then open:

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

### Phase 2B smoke test

The RoutineAgent review endpoint accepts a target date and returns deterministic progress with a structured MockProvider review:

```bash
curl -X POST http://localhost:8000/api/routine/agent/review \
	-H "Content-Type: application/json" \
	-d '{"date":"2026-09-06"}'
```

The response contains `progress` and a `review` with `summary`, `observations`, `recommendations`, and `tomorrow_priorities`.

### Phase 3B smoke test

The Learning Agent recommendation endpoint accepts an optional goal ID. Ownership is resolved from the configured active development user; `user_id`, tool selection, provider selection, and unknown fields are rejected.

```bash
curl -X POST http://localhost:8000/api/learning/agent/recommend \
	-H "Content-Type: application/json" \
	-d '{}'
```

The response contains deterministic `progress` and a typed `recommendation` with `summary`, `observations`, `recommendations`, and `next_steps`. Phase 3B uses the deterministic `MockProvider`; it does not integrate a real LLM, external research, or scheduling.

### Phase 3C session history

Create a session for an owned learning goal:

```bash
curl -X POST http://localhost:8000/api/learning/sessions \
	-H "Content-Type: application/json" \
	-d '{"goal_id":"<owned-goal-id>","started_at":"2026-09-06T09:00:00Z","ended_at":"2026-09-06T09:45:00Z","duration_minutes":45,"notes":"Reviewed SQL joins"}'
```

List the current user's sessions, optionally filtered by an owned goal:

```bash
curl "http://localhost:8000/api/learning/sessions?goal_id=<owned-goal-id>"
```

Session ownership is resolved from the configured development user. Cross-user goals and sessions are not accessible, and recorded session minutes update deterministic learning progress. The Learning Agent remains read-only and has no session-writing tool.

### Phase 3D goal API

The Learning MVP can be started through the public API by creating and retrieving owner-scoped goals:

```bash
curl -X POST http://localhost:8000/api/learning/goals \
	-H "Content-Type: application/json" \
	-d '{"title":"Python fundamentals","description":"Build stronger Python skills","priority":"high","target_date":"2026-12-31"}'

curl http://localhost:8000/api/learning/goals
curl http://localhost:8000/api/learning/goals/<goal-id>
```

Goal ownership comes from the configured current development user. A created goal is immediately included in deterministic learning progress and can be used with the session API. Goal updates and deletion are not part of the current MVP.

### Phase 4C job analysis

Analyze an existing owned job opportunity without changing it:

```bash
curl -X POST http://localhost:8000/api/jobs/<job-id>/agent/analyze \
	-H "Content-Type: application/json" \
	-d '{}'
```

The analysis is read-only and owner-scoped. `JOB_PROVIDER=mock` is the default and uses the deterministic `MockJobProvider` without network access. Explicit `JOB_PROVIDER=llm` uses the official OpenAI Responses API with strict Pydantic `JobAnalysis` output, a configured timeout, `store=False`, no model tools, and bounded input/output. The provider receives only the saved job fields as untrusted data; it never fetches the job URL, accesses Routine or Learning data, persists analysis, changes job status, or performs autonomous actions.

LLM mode requires these environment variables:

```text
JOB_PROVIDER="llm"
OPENAI_API_KEY="..."
OPENAI_MODEL="..."
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=1000
JOB_ANALYSIS_MAX_INPUT_CHARS=20000
```

Provider failures, missing configuration, refusals, incomplete responses, malformed output, and oversized input return the existing safe `503 Service Unavailable` behavior. Tests use fake clients and do not require an API key or network access.

### Phase 4D application tracking

Track a user-controlled application for an owned, non-archived job opportunity:

```bash
curl -X POST http://localhost:8000/api/applications \
	-H "Content-Type: application/json" \
	-d '{"job_id":"<owned-job-id>","notes":"Submitted through the company portal","next_action":"Follow up"}'

curl http://localhost:8000/api/applications
curl http://localhost:8000/api/applications/<application-id>
curl -X PATCH http://localhost:8000/api/applications/<application-id> \
	-H "Content-Type: application/json" \
	-d '{"status":"interviewing","next_action":"Prepare for screening"}'
```

Applications are owner-scoped and use the deterministic lifecycle `applied`, `interviewing`, `offer`, `rejected`, or `withdrawn`. One active application is allowed per user and job. This phase has no Application Agent, LLM calls, event history, resume handling, external integrations, or autonomous actions.

### Phase 5 stock quote MVP

Retrieve an informational stock quote without database persistence, an LLM, an agent, or trading actions:

```bash
curl http://localhost:8000/api/stocks/AAPL
```

`STOCK_PROVIDER="mock"` is the safe default and returns deterministic test data. Set `STOCK_PROVIDER="alphavantage"` with `ALPHAVANTAGE_API_KEY` to use the official Alpha Vantage `GLOBAL_QUOTE` endpoint. `ALPHAVANTAGE_API_BASE_URL` is configuration-controlled and `STOCK_TIMEOUT_SECONDS` bounds the request. Alpha Vantage's default quote entitlement is end-of-day; the response exposes this as `market_data_status` rather than claiming realtime data.

The endpoint is informational only. Phase 5 has no database tables or migrations, watchlists, historical persistence, LLM analysis, Stock Agent, brokerage integration, trading, recommendations, or portfolio actions.

### Phase 6 deterministic orchestrator

The orchestrator accepts one high-level request and dispatches exactly one registered, read-only capability:

```bash
curl -X POST http://localhost:8000/api/orchestrator/run \
	-H "Content-Type: application/json" \
	-d '{"message":"What is the current price of AAPL?"}'
```

Supported capabilities are `learning.recommend`, `job.analyze`, and `stock.quote`. Routing is deterministic and uses a static registry; no LLM planner, arbitrary tools, SQL, URLs, filesystem access, writes, agent-to-agent calls, or workflow persistence are available. The current-user dependency and existing downstream ownership checks remain authoritative. Routine is excluded because its current data is global and its agent includes write-capable tools. Application Tracking is excluded because its operations mutate state.
### Phase 4A manual job tracking

Phase 4A stores user-provided job opportunities without external discovery or application automation. The URL is inert reference data, and `description_snapshot` is stored exactly as supplied by the user.

```bash
curl -X POST http://localhost:8000/api/jobs \
	-H "Content-Type: application/json" \
	-d '{"title":"Backend Engineer","company":"Example Inc","url":"https://example.com/jobs/1","description_snapshot":"Paste the job description here","notes":"Review later"}'

curl http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs/<job-id>
curl -X PATCH http://localhost:8000/api/jobs/<job-id> \
	-H "Content-Type: application/json" \
	-d '{"notes":"Updated notes","status":"reviewing"}'
curl -X POST http://localhost:8000/api/jobs/<job-id>/archive
```

All job operations are owner-scoped through the configured development user. Phase 4A has no JobAgent, applications, resume handling, external network access, or real LLM provider.

### Phase 9 local agentic planner

The agentic runtime accepts a user goal, requests one structured decision from
the configured `PlannerProvider`, validates it, executes an approved capability,
normalizes the observation, and asks the planner again. The planner never
receives database sessions, repositories, secrets, or arbitrary network access.

OpenAI remains an optional cloud provider. For local verification, install
Ollama separately, confirm a model is installed with `ollama list`, and set the
root `.env` file to the installed model:

```text
AGENT_PLANNER_PROVIDER="local"
AGENT_PLANNER_MODEL="<installed-ollama-model>"
AGENT_PLANNER_LOCAL_BASE_URL="http://localhost:11434"
AGENT_PLANNER_LOCAL_TIMEOUT_SECONDS=30
```

The local provider uses only Ollama's localhost `/api/chat` endpoint and
validates the returned JSON before the runtime can execute anything. It is not
the default and fails clearly if Ollama or the selected model is unavailable.
The existing `AGENT_PLANNER_PROVIDER="llm"` setting continues to use the
OpenAI planner and its existing environment configuration.

### Phase 10 production deployment preparation

The intended deployment topology is Vercel for the Next.js frontend, Render
for the FastAPI backend, and managed PostgreSQL. Production must provide
`ENVIRONMENT="production"`, `AUTH_MODE="oidc"`, an HTTPS Auth0 callback and
frontend redirect, a random `SECRET_KEY`, an exact HTTPS
`BACKEND_CORS_ORIGINS` JSON array, and `DATABASE_URL` for the managed database.
For a Vercel frontend calling a Render backend, use
`AUTH_COOKIE_SAMESITE="none"` with HTTPS and keep CSRF protection enabled.

Render backend commands:

```text
Build: pip install -r requirements.txt
Pre-deploy: alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health check: /api/health
```

Set the Vercel environment variable `NEXT_PUBLIC_API_URL` to the deployed
Render backend URL. Do not deploy Ollama to Render.

The no-cost production default is the deterministic rule-based planner, which
requires no OpenAI API key or credits:

```text
AGENT_PLANNER_PROVIDER="rule_based"
```

The hosted `llm` planner remains available as an optional production setting.
It requires both `OPENAI_API_KEY` and `AGENT_PLANNER_MODEL`; production
rejects `llm` if either is missing:

```text
AGENT_PLANNER_PROVIDER="llm"
AGENT_PLANNER_MODEL="<hosted-model>"
OPENAI_API_KEY="<secret-managed-by-render>"
```

Production only accepts `AGENT_PLANNER_PROVIDER` values of `rule_based` or
`llm`; `local` (Ollama) is rejected because Ollama must not be deployed to
Render.

Never place production credentials in this repository or in `.env.example`.

## Commands

```bash
make backend-test
make backend-lint
make alembic-upgrade
make backend-run
```

## Notes

- The system keeps the user in the loop for sensitive actions.
- AI agents are intentionally designed as recommenders and assistants instead of autonomous actors for high-risk actions.
- The project is built to support future extension with orchestration, persistence, and provider abstractions.

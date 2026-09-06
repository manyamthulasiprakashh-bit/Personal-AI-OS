# Personal AI-OS

Personal AI-OS is a portfolio-grade monorepo for orchestrating personal productivity, learning, job search, and stock market analysis with a multi-agent architecture.

## Current status

Phase 1, Phase 2B, Phase 3A, Phase 3B, and Phase 3C are complete. The repository currently contains:

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

## Development roadmap

1. Phase 1: Project foundation
2. Phase 2: Daily Routine Agent MVP (Phase 2B complete)
3. Phase 3: Learning Agent MVP (Phase 3A, Phase 3B, and Phase 3C complete)
4. Phase 4: Job Application Agent MVP
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

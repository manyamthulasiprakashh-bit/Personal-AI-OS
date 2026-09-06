# Personal AI-OS

Personal AI-OS is a portfolio-grade monorepo for orchestrating personal productivity, learning, job search, and stock market analysis with a multi-agent architecture.

## Phase 1 status

This repository currently contains the project foundation only, as required by the phased implementation plan:

- FastAPI backend foundation
- SQLAlchemy + PostgreSQL configuration
- Alembic migration scaffolding
- Docker Compose services
- Basic Next.js frontend shell
- Health and dashboard endpoints
- Logging, env configuration, and tests

## Development roadmap

1. Phase 1: Project foundation
2. Phase 2: Daily Routine Agent MVP
3. Phase 3: Learning Agent MVP
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
├── docker-compose.yml
├── Makefile
├── README.md
└── .gitignore
```

## Local development

```bash
cp .env.example .env
make backend-install
make frontend-install
make up
```

Then open:

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Commands

```bash
make backend-test
make backend-lint
make alembic-upgrade
make compose-up
```

## Notes

- The system keeps the user in the loop for sensitive actions.
- AI agents are intentionally designed as recommenders and assistants instead of autonomous actors for high-risk actions.
- The project is built to support future extension with orchestration, persistence, and provider abstractions.

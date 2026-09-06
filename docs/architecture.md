# Architecture Overview

## Core principles

- Keep the user as the final decision-maker for all sensitive actions.
- Separate orchestration, agents, shared memory, and provider abstractions.
- Favor explicit interfaces and clean boundaries over hidden coupling.
- Keep security and auditability as first-class concerns.

## Initial phase

The repository currently implements Phase 1 responsibilities:

- FastAPI app shell with health and dashboard endpoints
- PostgreSQL / SQLAlchemy-ready configuration
- Alembic migration layout
- Docker Compose configuration for backend, frontend, and Postgres
- Basic Next.js dashboard shell
- Structured logging and environment configuration

## Planned architecture

- Orchestrator coordinates agent execution and approval requests.
- Agents expose tool-based interfaces and operate on the shared memory layer.
- Shared memory persists user, job, learning, and market data in PostgreSQL.
- The LLM provider abstraction allows provider changes without affecting business logic.
- Dashboard reads aggregated state from backend APIs.

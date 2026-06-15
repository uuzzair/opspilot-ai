# OpsPilot AI - Project Spec

## Goal

Build a production-style AI incident triage backend using FastAPI, PostgreSQL, Redis, Celery, pgvector, and LangGraph.

The app should allow engineers to submit incidents, run asynchronous AI triage, retrieve relevant runbooks, generate structured remediation suggestions, and require human approval before marking recommendations as accepted.

## Non-goals

- No complex frontend initially.
- No direct execution of remediation commands.
- No LLM-generated SQL execution.
- No fake “chatbot-only” demo.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL
- pgvector
- Redis
- Celery
- LangGraph
- Pydantic v2
- Pytest
- Docker Compose
- GitHub Actions

## Core Entities

- User
- Incident
- TriageResult
- Runbook
- RunbookChunk
- AuditLog

## Required Features

### Phase 1

- FastAPI app
- Docker Compose with API, PostgreSQL, Redis
- health endpoint
- SQLAlchemy setup
- Alembic migrations
- environment-based settings

### Phase 2

- User model
- Incident model
- TriageResult model
- Runbook model
- CRUD APIs
- Pydantic schemas

### Phase 3

- LangGraph triage workflow
- severity classification
- runbook retrieval
- structured triage output
- output validation

### Phase 4

- Celery background jobs
- async triage endpoint
- audit logging

### Phase 5

- tests
- CI pipeline
- README documentation
- sample runbooks
- sample incidents

## Engineering Rules

- Keep business logic out of route handlers.
- Use services for domain logic.
- Use Pydantic schemas for API boundaries.
- Use Alembic for all DB schema changes.
- Do not trust LLM output.
- Validate all LLM responses with schemas.
- Add tests for every endpoint.
- Use structured logging.
- Use Docker Compose for local development.
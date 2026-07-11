# OpsPilot AI

OpsPilot AI is a production-style backend for incident triage. It lets engineers create incidents, manage runbooks, retrieve relevant runbook chunks with local embeddings, generate structured triage through a LangGraph workflow, submit triage jobs to Celery, and require human approval before recommendations are accepted.

The project is backend-only. There is no frontend yet.

## Architecture Summary

- FastAPI exposes REST APIs under `/api`, with `/health` kept outside the API prefix.
- SQLAlchemy 2.0 models persist users, incidents, runbooks, triage results, triage jobs, and audit logs.
- PostgreSQL stores application data. pgvector stores runbook chunk embeddings.
- Redis is used as the Celery broker and result backend.
- Celery workers run long triage jobs outside request/response handling.
- LangGraph orchestrates deterministic triage nodes and calls a pluggable triage provider.
- The default provider is deterministic. Ollama can be enabled for local LLM output.
- Audit logs record important state-changing actions.

More detail: [docs/architecture.md](docs/architecture.md).

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL + pgvector
- Redis
- Celery
- LangGraph
- Pydantic v2
- sentence-transformers
- Pytest
- Docker Compose

## Features

- User registration, login, and `/api/auth/me`
- JWT access tokens
- Incident CRUD
- Runbook CRUD and chunk management
- Local embeddings for runbook chunks
- Runbook semantic search
- Synchronous incident triage
- Asynchronous triage jobs with Celery
- Deterministic triage fallback
- Optional local Ollama triage provider
- Human approval/rejection for triage results
- Audit log listing and filtering
- Docker Compose development stack

## Local Setup

Use Python 3.11.8 or newer.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

PostgreSQL and Redis are expected to run through Docker Compose, not local installs.

## Docker Setup

Start API, worker, PostgreSQL, and Redis:

```powershell
docker compose up --build
```

Run in the background:

```powershell
docker compose up -d --build
```

Check services:

```powershell
docker compose ps
docker compose logs -f api
docker compose logs -f worker
```

API docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## Environment Variables

Use `.env.example` as the safe template. Keep real `.env` values private.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database URL |
| `REDIS_URL` | Redis broker/result URL for Celery |
| `JWT_SECRET_KEY` | JWT signing secret |
| `JWT_ALGORITHM` | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `LLM_PROVIDER` | `deterministic` or `ollama` |
| `OLLAMA_BASE_URL` | Ollama HTTP endpoint |
| `OLLAMA_MODEL` | Local Ollama model, for example `qwen3:4b` |
| `OLLAMA_TIMEOUT_SECONDS` | Timeout for local Ollama generation |
| `OPENAI_API_KEY` | Reserved for future OpenAI support |
| `OPENAI_MODEL` | Reserved for future OpenAI support |
| `EMBEDDING_MODEL_NAME` | sentence-transformers model |

ChatGPT Plus is separate from OpenAI API billing and API keys. This project does not require an OpenAI API key. Local Ollama can be used instead by setting:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_TIMEOUT_SECONDS=90
```

Use `http://host.docker.internal:11434` when the API runs in Docker and Ollama runs on your host machine.

## Database Migrations

Apply migrations:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

Create a migration after model changes:

```powershell
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "Describe change"
```

For Docker PostgreSQL from the host:

```powershell
$env:DATABASE_URL='postgresql://opspilot:opspilot@localhost:5432/opspilot_db'
.\venv\Scripts\python.exe -m alembic upgrade head
```

## Test Commands

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe -m ruff check app tests
docker compose config --quiet
.\venv\Scripts\python.exe -m pip check
```

## Windows Helper Script

Common commands are available in `scripts/dev.ps1`:

```powershell
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
.\scripts\dev.ps1 compose-check
.\scripts\dev.ps1 migrate
```

## Sample API Flow

Detailed curl examples are in [docs/api-examples.md](docs/api-examples.md).

Short flow:

1. Register: `POST /api/auth/register`
2. Login: `POST /api/auth/login`
3. Create an incident: `POST /api/incidents`
4. Create a runbook: `POST /api/runbooks`
5. Add runbook chunks: `POST /api/runbooks/{runbook_id}/chunks`
6. Run synchronous triage: `POST /api/incidents/{incident_id}/triage`
7. Approve or reject triage: `POST /api/triage/{triage_id}/approve`
8. View audit logs: `GET /api/audit-logs`

## Async Triage Job Flow

Create a job:

```powershell
curl -X POST http://localhost:8000/api/incidents/INCIDENT_ID/triage-jobs `
  -H "Authorization: Bearer TOKEN"
```

Poll status:

```powershell
curl http://localhost:8000/api/triage-jobs/JOB_ID `
  -H "Authorization: Bearer TOKEN"
```

The POST returns immediately with `202 Accepted`. The Celery worker creates the triage result later and updates the job to `succeeded` or `failed`.

## Sample Data

- `samples/runbooks/payments-api-latency.md`
- `samples/incidents/payments-api-latency.json`

These are human-readable examples for manual testing.

## Security And Production Notes

- Do not commit `.env`.
- Replace `JWT_SECRET_KEY` before real deployment.
- Store secrets in a real secret manager in production.
- Keep PostgreSQL and Redis private to the application network.
- Audit logs intentionally store metadata only, not passwords, JWTs, full incident descriptions, or full runbook chunk text.
- LLM output is validated with Pydantic before persistence.
- Human approval exists because generated triage is advisory and should not be treated as an accepted remediation plan without review.
- Async triage jobs are not idempotent yet. If a worker crashes after creating a triage result but before updating the job, an orphaned result may exist.

## CI

GitHub Actions workflow lives at `.github/workflows/ci.yml` and runs:

- dependency install
- tests
- ruff lint
- Docker Compose config validation

## License

Proprietary - OpsPilot AI

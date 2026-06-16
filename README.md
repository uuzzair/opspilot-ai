# OpsPilot AI - Production-Style Backend

A production-style backend for AI-powered incident triage built with FastAPI, PostgreSQL, Redis, and LangGraph.

## Phase 1: Core Infrastructure

This is Phase 1 implementation with foundational infrastructure:
- FastAPI application with health check endpoints
- PostgreSQL database with SQLAlchemy 2.0 ORM
- Redis for caching and task queues (prepared for future Celery integration)
- Alembic database migrations
- Docker Compose for local development
- Structured logging with JSON output
- Pytest test suite
- Environment-based configuration

## Prerequisites

- **Python 3.11.8** (or higher)
- **Docker Desktop** (for PostgreSQL and Redis)
- **Git**

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd opspilot-ai

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# The .env file is configured for Docker Compose with defaults
```

### 3. Start Services with Docker Compose

```bash
# Start all services (API, PostgreSQL, Redis)
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Initialize Database

```bash
# Create initial migration (first time only)
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Verify connection
python -c "from app.db.session import engine; engine.execute('SELECT 1')"
```

### 5. Run the Application

The API is automatically running via Docker Compose on `http://localhost:8000`

```bash
# Test health endpoint
curl http://localhost:8000/health

# OpenAPI documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## Running Tests Locally

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_health.py -v
```

## Project Structure

```
opspilot-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py         # Pydantic settings (environment config)
│   │   └── logging.py          # Structured logging setup
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # SQLAlchemy session and engine
│   │   └── models.py           # ORM models (BaseModel)
│   └── api/
│       ├── __init__.py
│       └── health.py           # Health check endpoints
├── alembic/
│   ├── env.py                  # Alembic environment config
│   ├── script.py.mako          # Migration template
│   └── versions/               # Migration files
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   └── test_health.py          # Health endpoint tests
├── .env.example                # Example environment variables
├── .env                        # Local environment (git-ignored)
├── .gitignore                  # Git ignore rules
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Docker Compose configuration
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── PROJECT_SPEC.md             # Project specification
└── README.md                   # This file
```

## Environment Variables

Key environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEBUG` | `false` | Enable debug mode |
| `DATABASE_URL` | `postgresql://opspilot:opspilot@localhost:5432/opspilot_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local LLM endpoint (future) |
| `OPENAI_API_KEY` | Empty | OpenAI API key (future) |
| `USE_LOCAL_LLM` | `true` | Use local Ollama by default |

## Available Endpoints

### Health Checks
- `GET /health` - Basic health check

### API Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI schema

## Development Workflow

### Making Database Schema Changes

```bash
# Create a new migration
alembic revision --autogenerate -m "Add users table"

# Review the generated migration in alembic/versions/

# Apply the migration
alembic upgrade head

# Roll back if needed
alembic downgrade -1
```

### Adding New Endpoints

1. Create route handlers in `app/api/` 
2. Add Pydantic schemas as needed
3. Import and register routers in `app/main.py`
4. Write tests in `tests/`
5. Update this README

### Debugging

```bash
# View database logs
docker-compose logs -f postgres

# View Redis logs
docker-compose logs -f redis

# View API logs with full output
docker-compose logs -f api

# Access PostgreSQL shell
docker-compose exec postgres psql -U opspilot -d opspilot_db

# Access Redis shell
docker-compose exec redis redis-cli
```

## Stopping Services

```bash
# Stop all services (keep volumes)
docker-compose stop

# Stop and remove containers (keep volumes)
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v
```

## Production Deployment

For production deployment:

1. Build production Docker image:
   ```bash
   docker build --target production -t opspilot-ai:latest .
   ```

2. Set production environment variables

3. Use a production database (managed PostgreSQL)

4. Use environment-based secrets management

5. Configure reverse proxy (nginx/Traefik)

6. Set up monitoring and logging aggregation

## Future Phases

- **Phase 2**: User, Incident, and Runbook models with CRUD APIs
- **Phase 3**: LangGraph triage workflow with LLM integration
- **Phase 4**: Celery background jobs for async triage
- **Phase 5**: Comprehensive tests and CI/CD pipeline

## Contributing

Follow these guidelines:
- Keep business logic in services, not route handlers
- Use Pydantic schemas for API boundaries
- Write tests for all new endpoints
- Use structured JSON logging
- Ensure type hints on all functions

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis Connection Issues
```bash
# Verify Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in docker-compose.yml
```

## License

Proprietary - OpsPilot AI

## Support

For issues and questions, please refer to the PROJECT_SPEC.md file.

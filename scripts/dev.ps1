param(
    [Parameter(Position = 0)]
    [ValidateSet("test", "lint", "compose-check", "migrate", "pip-check", "up", "down", "logs-api", "logs-worker")]
    [string] $Command = "test"
)

$ErrorActionPreference = "Stop"

switch ($Command) {
    "test" {
        .\venv\Scripts\python.exe -m pytest
    }
    "lint" {
        .\venv\Scripts\python.exe -m ruff check app tests
    }
    "compose-check" {
        docker compose config --quiet
    }
    "migrate" {
        .\venv\Scripts\python.exe -m alembic upgrade head
    }
    "pip-check" {
        .\venv\Scripts\python.exe -m pip check
    }
    "up" {
        docker compose up --build
    }
    "down" {
        docker compose down
    }
    "logs-api" {
        docker compose logs -f api
    }
    "logs-worker" {
        docker compose logs -f worker
    }
}

"""Application settings and environment configuration."""
from typing import Any

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    app_name: str = "OpsPilot AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str
    database_echo: bool = False

    # Redis
    redis_url: str

    # LLM (future support for OpenAI and Ollama)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Use Ollama by default, switch to OpenAI when available.
    use_local_llm: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        """Handle deployment-style DEBUG values from the host environment."""
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

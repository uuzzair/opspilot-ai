"""Pluggable triage generation providers."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal, Protocol
from urllib import error, request

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.triage_state import RetrievedChunk
from app.core.logging import get_logger
from app.core.settings import get_settings

DETERMINISTIC_MODEL_NAME = "langgraph-deterministic-v1"
logger = get_logger(__name__)


class TriageGeneration(BaseModel):
    """Validated provider output for triage generation."""

    model_config = ConfigDict(extra="ignore")

    summary: str = Field(min_length=1)
    suspected_cause: str | None = None
    recommended_actions: list[str] = Field(min_length=1)
    confidence_score: float = Field(ge=0, le=1)


class TriageProviderResult(TriageGeneration):
    """Provider output plus trusted provider metadata."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str


class TriageProvider(Protocol):
    """Interface for triage generation providers."""

    def generate_triage(
        self,
        incident_text: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        severity: str,
        affected_service: str | None = None,
        title: str | None = None,
    ) -> TriageProviderResult:
        """Generate structured triage output."""


class DeterministicTriageProvider:
    """Test-safe deterministic triage provider."""

    model_name = DETERMINISTIC_MODEL_NAME

    def __init__(self, fallback_actions: Sequence[str]) -> None:
        self.fallback_actions = list(fallback_actions)

    def generate_triage(
        self,
        incident_text: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        severity: str,
        affected_service: str | None = None,
        title: str | None = None,
    ) -> TriageProviderResult:
        """Generate deterministic triage output from retrieved chunks."""
        actions = [
            chunk["chunk_text"].strip()
            for chunk in retrieved_chunks
            if chunk["chunk_text"].strip()
        ] or self.fallback_actions
        chunks_found = bool(retrieved_chunks)
        service = affected_service or "an unspecified service"
        incident_title = title or incident_text[:80].strip()
        return TriageProviderResult(
            summary=f"{severity.title()} incident for {service}: {incident_title}",
            suspected_cause=(
                "Relevant runbook context was found for this incident."
                if chunks_found
                else f"No matching runbook context found; classified as {severity} from incident text."
            ),
            recommended_actions=actions,
            confidence_score=0.75 if chunks_found else 0.45,
            model_name=self.model_name,
        )


class OllamaTriageProvider:
    """Optional local Ollama provider with deterministic fallback."""

    def __init__(
        self,
        base_url: str,
        model: str,
        fallback_provider: TriageProvider,
        timeout_seconds: float = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_provider = fallback_provider
        self.timeout_seconds = timeout_seconds

    @property
    def model_name(self) -> str:
        """Trusted model label for persisted triage results."""
        return f"langgraph-ollama-{self.model}"

    def generate_triage(
        self,
        incident_text: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        severity: str,
        affected_service: str | None = None,
        title: str | None = None,
    ) -> TriageProviderResult:
        """Generate structured triage output through Ollama, falling back safely."""
        try:
            generation = self._request_generation(
                incident_text=incident_text,
                retrieved_chunks=retrieved_chunks,
                severity=severity,
                affected_service=affected_service,
                title=title,
            )
            return TriageProviderResult(
                **generation.model_dump(),
                model_name=self.model_name,
            )
        except (OSError, ValueError, ValidationError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
            logger.warning(
                "Ollama triage generation failed; falling back to deterministic provider",
                extra={
                    "provider": "ollama",
                    "model": self.model,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return self.fallback_provider.generate_triage(
                incident_text=incident_text,
                retrieved_chunks=retrieved_chunks,
                severity=severity,
                affected_service=affected_service,
                title=title,
            )

    def _request_generation(
        self,
        incident_text: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        severity: str,
        affected_service: str | None,
        title: str | None,
    ) -> TriageGeneration:
        """Call Ollama and validate its structured response."""
        payload = {
            "model": self.model,
            "prompt": self._build_prompt(
                incident_text=incident_text,
                retrieved_chunks=retrieved_chunks,
                severity=severity,
                affected_service=affected_service,
                title=title,
            ),
            "stream": False,
            "format": "json",
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
        envelope = json.loads(raw_body)
        raw_generation: Any = envelope.get("response") or envelope.get("thinking")
        if isinstance(raw_generation, str):
            return TriageGeneration.model_validate_json(raw_generation)
        if isinstance(raw_generation, dict):
            return TriageGeneration.model_validate(raw_generation)
        raise ValueError("Ollama response did not include structured JSON")

    def _build_prompt(
        self,
        incident_text: str,
        retrieved_chunks: Sequence[RetrievedChunk],
        severity: str,
        affected_service: str | None,
        title: str | None,
    ) -> str:
        """Build a prompt that asks for structured JSON only."""
        chunk_lines = [
            f"- {chunk['chunk_text']}"
            for chunk in retrieved_chunks
            if chunk["chunk_text"].strip()
        ]
        chunk_context = "\n".join(chunk_lines) if chunk_lines else "No matching runbook chunks."
        return (
            "Generate incident triage as JSON only. "
            "Use keys: summary, suspected_cause, recommended_actions, confidence_score. "
            "confidence_score must be between 0 and 1.\n"
            f"Severity: {severity}\n"
            f"Service: {affected_service or 'unspecified'}\n"
            f"Title: {title or 'unspecified'}\n"
            f"Incident: {incident_text}\n"
            f"Runbook context:\n{chunk_context}"
        )


def get_triage_provider(
    fallback_actions: Sequence[str],
    provider_name: Literal["deterministic", "ollama"] | str | None = None,
) -> TriageProvider:
    """Build the configured triage provider."""
    settings = get_settings()
    deterministic = DeterministicTriageProvider(fallback_actions)
    selected_provider = provider_name or settings.llm_provider
    if selected_provider == "ollama":
        return OllamaTriageProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            fallback_provider=deterministic,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
    return deterministic

"""Tests for triage LLM provider abstraction."""
import json
from urllib import error
from uuid import uuid4

from app.ai.llm_provider import (
    DETERMINISTIC_MODEL_NAME,
    DeterministicTriageProvider,
    OllamaTriageProvider,
)
from app.ai.triage_graph import FALLBACK_ACTIONS
from app.ai.triage_state import RetrievedChunk


class MockHTTPResponse:
    """Minimal context manager for urllib response tests."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def retrieved_chunk(text: str = "Check service dashboard.") -> RetrievedChunk:
    """Build a retrieved chunk for provider tests."""
    return {
        "runbook_id": uuid4(),
        "chunk_id": uuid4(),
        "chunk_text": text,
        "chunk_index": 0,
        "service_name": "payments-api",
        "distance": 0.1,
    }


def deterministic_provider() -> DeterministicTriageProvider:
    """Build a deterministic provider for tests."""
    return DeterministicTriageProvider(FALLBACK_ACTIONS)


def test_deterministic_provider_returns_valid_structured_output() -> None:
    """Deterministic provider returns validated triage output."""
    provider = deterministic_provider()

    result = provider.generate_triage(
        incident_text="High latency on payments",
        retrieved_chunks=[retrieved_chunk("Review p95 dashboard.")],
        severity="high",
        affected_service="payments-api",
        title="High latency on payments",
    )

    assert result.summary == "High incident for payments-api: High latency on payments"
    assert result.suspected_cause == "Relevant runbook context was found for this incident."
    assert result.recommended_actions == ["Review p95 dashboard."]
    assert result.confidence_score == 0.75
    assert result.model_name == DETERMINISTIC_MODEL_NAME


def test_ollama_provider_parses_valid_mocked_structured_json(monkeypatch) -> None:
    """Ollama provider validates structured JSON from a mocked response."""
    payload = {
        "response": json.dumps(
            {
                "summary": "High incident for payments-api.",
                "suspected_cause": "Upstream latency.",
                "recommended_actions": ["Check upstream dependency health."],
                "confidence_score": 0.82,
            }
        )
    }

    def mock_urlopen(req, timeout):
        return MockHTTPResponse(payload)

    monkeypatch.setattr("app.ai.llm_provider.request.urlopen", mock_urlopen)
    provider = OllamaTriageProvider(
        base_url="http://ollama.local",
        model="llama3.1",
        fallback_provider=deterministic_provider(),
    )

    result = provider.generate_triage(
        incident_text="High latency on payments",
        retrieved_chunks=[retrieved_chunk()],
        severity="high",
        affected_service="payments-api",
        title="High latency on payments",
    )

    assert result.summary == "High incident for payments-api."
    assert result.recommended_actions == ["Check upstream dependency health."]
    assert result.confidence_score == 0.82
    assert result.model_name == "langgraph-ollama-llama3.1"


def test_ollama_provider_falls_back_on_invalid_json(monkeypatch) -> None:
    """Invalid Ollama output falls back to deterministic provider."""
    payload = {"response": "not-json"}

    def mock_urlopen(req, timeout):
        return MockHTTPResponse(payload)

    monkeypatch.setattr("app.ai.llm_provider.request.urlopen", mock_urlopen)
    provider = OllamaTriageProvider(
        base_url="http://ollama.local",
        model="llama3.1",
        fallback_provider=deterministic_provider(),
    )

    result = provider.generate_triage(
        incident_text="Payment failure",
        retrieved_chunks=[],
        severity="critical",
        affected_service="payments-api",
        title="Payment failure",
    )

    assert result.model_name == DETERMINISTIC_MODEL_NAME
    assert result.recommended_actions == FALLBACK_ACTIONS
    assert result.confidence_score == 0.45


def test_ollama_provider_falls_back_on_http_error(monkeypatch) -> None:
    """HTTP failures fall back to deterministic provider."""
    def mock_urlopen(req, timeout):
        raise error.URLError("connection refused")

    monkeypatch.setattr("app.ai.llm_provider.request.urlopen", mock_urlopen)
    provider = OllamaTriageProvider(
        base_url="http://ollama.local",
        model="llama3.1",
        fallback_provider=deterministic_provider(),
    )

    result = provider.generate_triage(
        incident_text="Intermittent timeout",
        retrieved_chunks=[],
        severity="medium",
        affected_service="checkout-api",
        title="Intermittent timeout",
    )

    assert result.model_name == DETERMINISTIC_MODEL_NAME
    assert result.summary == "Medium incident for checkout-api: Intermittent timeout"

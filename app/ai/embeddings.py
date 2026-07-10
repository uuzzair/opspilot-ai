"""Local embedding generation."""
from functools import cached_property

from app.core.settings import get_settings


class EmbeddingService:
    """Generate text embeddings using a local sentence-transformers model."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model_name

    @cached_property
    def model(self):
        """Load the embedding model lazily."""
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> list[float]:
        """Generate a normalized embedding for one text value."""
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [float(value) for value in embedding.tolist()]

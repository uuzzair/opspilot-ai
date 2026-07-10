"""Custom SQLAlchemy types."""
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator


class EmbeddingVector(TypeDecorator):
    """Use pgvector on PostgreSQL and JSON for local SQLite tests."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int = 384, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        """Select a dialect-specific column type."""
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())

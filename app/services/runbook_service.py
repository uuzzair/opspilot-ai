"""Runbook business operations."""
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.db.models import Runbook, RunbookChunk
from app.schemas.runbook import (
    RunbookChunkCreate,
    RunbookChunkSearchResult,
    RunbookCreate,
    RunbookSearchRequest,
    RunbookUpdate,
)

embedding_service = EmbeddingService()


def create_runbook(
    db: Session,
    runbook_in: RunbookCreate,
    created_by_id: UUID,
) -> Runbook:
    """Create a runbook."""
    runbook = Runbook(**runbook_in.model_dump(), created_by_id=created_by_id)
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def list_runbooks(db: Session, limit: int = 50, offset: int = 0) -> list[Runbook]:
    """List runbooks ordered by creation time."""
    result = db.execute(
        select(Runbook)
        .order_by(Runbook.created_at.desc(), Runbook.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


def get_runbook(db: Session, runbook_id: UUID) -> Runbook | None:
    """Get a runbook by ID."""
    return db.get(Runbook, runbook_id)


def update_runbook(
    db: Session,
    runbook: Runbook,
    runbook_in: RunbookUpdate,
) -> Runbook:
    """Update a runbook."""
    update_data = runbook_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(runbook, field, value)

    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def create_runbook_chunk(
    db: Session,
    runbook: Runbook,
    chunk_in: RunbookChunkCreate,
) -> RunbookChunk:
    """Create a runbook chunk."""
    embedding = embedding_service.embed_text(chunk_in.chunk_text)
    chunk = RunbookChunk(
        runbook_id=runbook.id,
        chunk_text=chunk_in.chunk_text,
        chunk_index=chunk_in.chunk_index,
        metadata_=chunk_in.metadata,
        embedding=embedding,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def list_runbook_chunks(db: Session, runbook_id: UUID) -> list[RunbookChunk]:
    """List chunks for a runbook ordered by chunk index."""
    result = db.execute(
        select(RunbookChunk)
        .where(RunbookChunk.runbook_id == runbook_id)
        .order_by(RunbookChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


def search_runbook_chunks(
    db: Session,
    search_in: RunbookSearchRequest,
) -> list[RunbookChunkSearchResult]:
    """Find similar runbook chunks for a text query."""
    query_embedding = embedding_service.embed_text(search_in.query)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        return search_runbook_chunks_postgres(db, search_in, query_embedding)
    return search_runbook_chunks_python(db, search_in, query_embedding)


def search_runbook_chunks_postgres(
    db: Session,
    search_in: RunbookSearchRequest,
    query_embedding: list[float],
) -> list[RunbookChunkSearchResult]:
    """Search chunks using pgvector distance in PostgreSQL."""
    where_clause = "WHERE rc.embedding IS NOT NULL"
    params: dict[str, object] = {
        "embedding": format_vector(query_embedding),
        "top_k": search_in.top_k,
    }
    if search_in.service_name is not None:
        where_clause += " AND rb.service_name = :service_name"
        params["service_name"] = search_in.service_name

    rows = db.execute(
        text(
            f"""
            SELECT
                rb.id AS runbook_id,
                rc.id AS chunk_id,
                rc.chunk_text AS chunk_text,
                rc.chunk_index AS chunk_index,
                rb.service_name AS service_name,
                rc.embedding <=> CAST(:embedding AS vector) AS distance
            FROM runbook_chunks rc
            JOIN runbooks rb ON rb.id = rc.runbook_id
            {where_clause}
            ORDER BY distance ASC
            LIMIT :top_k
            """
        ),
        params,
    )
    return [
        RunbookChunkSearchResult(
            runbook_id=row.runbook_id,
            chunk_id=row.chunk_id,
            chunk_text=row.chunk_text,
            chunk_index=row.chunk_index,
            service_name=row.service_name,
            distance=float(row.distance),
        )
        for row in rows
    ]


def search_runbook_chunks_python(
    db: Session,
    search_in: RunbookSearchRequest,
    query_embedding: list[float],
) -> list[RunbookChunkSearchResult]:
    """Search chunks in Python for SQLite tests."""
    statement = select(RunbookChunk, Runbook).join(Runbook)
    if search_in.service_name is not None:
        statement = statement.where(Runbook.service_name == search_in.service_name)

    matches: list[RunbookChunkSearchResult] = []
    for chunk, runbook in db.execute(statement).all():
        if chunk.embedding is None:
            continue
        matches.append(
            RunbookChunkSearchResult(
                runbook_id=runbook.id,
                chunk_id=chunk.id,
                chunk_text=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                service_name=runbook.service_name,
                distance=cosine_distance(query_embedding, chunk.embedding),
            )
        )
    return sorted(matches, key=lambda match: match.distance)[: search_in.top_k]


def cosine_distance(left: list[float], right: list[float]) -> float:
    """Compute cosine distance for normalized or unnormalized vectors."""
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 1.0
    return 1.0 - (dot / (left_norm * right_norm))


def format_vector(values: list[float]) -> str:
    """Format a vector literal for pgvector."""
    return "[" + ",".join(str(value) for value in values) + "]"

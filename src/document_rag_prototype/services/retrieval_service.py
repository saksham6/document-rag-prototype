from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.services.embedding_service import embed_texts
from document_rag_prototype.api.schemas.models import SearchResult


async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    knowledge_base_id: int | None = None,
    document_id: int | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty.")

    top_k = max(1, min(top_k, 20))

    query_embedding = embed_texts([query])[0]
    query_embedding_str = "[" + ",".join(str(value) for value in query_embedding) + "]"

    sql = """
        SELECT
            chunks.id AS chunk_id,
            chunks.document_id AS document_id,
            documents.filename AS filename,
            chunks.chunk_index AS chunk_index,
            chunks.page_number AS page_number,
            chunks.content AS content,
            chunks.embedding <=> CAST(:query_embedding AS vector) AS distance
        FROM chunks
        JOIN documents ON documents.id = chunks.document_id
        WHERE chunks.embedding IS NOT NULL
    """

    params = {
        "query_embedding": query_embedding_str,
        "top_k": top_k,
    }

    if knowledge_base_id is not None:
        sql += " AND documents.knowledge_base_id = :knowledge_base_id"
        params["knowledge_base_id"] = knowledge_base_id

    if document_id is not None:
        sql += " AND chunks.document_id = :document_id"
        params["document_id"] = document_id

    sql += """
        ORDER BY distance ASC
        LIMIT :top_k
    """

    result = await db.execute(text(sql), params)
    rows = result.mappings().all()

    return [
        SearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            filename=row["filename"],
            chunk_index=row["chunk_index"],
            page_number=row["page_number"],
            content=row["content"],
            distance=float(row["distance"]),
        )
        for row in rows
    ]
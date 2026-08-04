from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.api.schemas.models import (
    SearchAnswerResponse,
    SearchAnswerSource,
    SearchRequest,
)
from document_rag_prototype.db.session import get_db_session
from document_rag_prototype.services.generation_service import generate_answer
from document_rag_prototype.services.retrieval_service import retrieve_chunks


router = APIRouter(tags=["RAG"])


@router.post("/search", response_model=SearchAnswerResponse)
async def semantic_search(
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db_session),
):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    try:
        chunks = await retrieve_chunks(
            query=query,
            db=db,
            knowledge_base_id=payload.knowledge_base_id,
            document_id=payload.document_id,
            top_k=5,
        )

        answer = await generate_answer(
            question=query,
            chunks=chunks,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search and answer generation failed: {exc}",
        ) from exc

    sources = [
        SearchAnswerSource(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            distance=chunk.distance,
        )
        for chunk in chunks
    ]

    return SearchAnswerResponse(
        query=query,
        answer=answer,
        sources=sources,
    )
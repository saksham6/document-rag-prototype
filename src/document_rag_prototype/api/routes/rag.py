from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.api.schemas.models import (
    SearchAnswerResponse,
    SearchAnswerSource,
    SearchRequest,
)
from document_rag_prototype.db.session import get_db_session
from document_rag_prototype.services.generation_service import generate_answer
from document_rag_prototype.services.retrieval_service import retrieve_chunks
from sqlalchemy import select

from document_rag_prototype.db.models import Document, KnowledgeBase
from document_rag_prototype.services.document_routing_service import (
    find_document_matches,
    resolve_document_match,
)


router = APIRouter(tags=["RAG"])


@router.post("/search", response_model=SearchAnswerResponse)
async def semantic_search(
    payload: SearchRequest,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    result = await db.execute(
    select(Document)
    .join(KnowledgeBase)
    .where(
        Document.knowledge_base_id == payload.knowledge_base_id,
        KnowledgeBase.workspace_id == x_workspace_id,
    )
    )

    documents = result.scalars().all()

    document_matches = find_document_matches(
    query=query,
    documents=documents,
    )

    print(
    "DOCUMENT MATCHES:",
    [
        {
            "document_id": item["document"].id,
            "filename": item["document"].filename,
            "score": item["score"],
        }
        
        for item in document_matches
    ],
    )

    resolved_document_id = payload.document_id

    if resolved_document_id is None:
        if len(documents) == 1:
            resolved_document_id = documents[0].id

        else:
            resolved_document = resolve_document_match(document_matches)

            if resolved_document is not None:
                resolved_document_id = resolved_document.id

            else:
                available_documents = [
                    {
                        "id": document.id,
                        "filename": document.filename,
                    }
                    for document in documents
                ]

                raise HTTPException(
                status_code=400,
                detail={
                    "message": "Your question does not clearly identify one document.",
                    "documents": available_documents,
                    "original_query": query,
                },
       )            

    try:
        chunks = await retrieve_chunks(
        query=query,
        db=db,
        workspace_id=x_workspace_id,
        knowledge_base_id=payload.knowledge_base_id,
        document_id=resolved_document_id,
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
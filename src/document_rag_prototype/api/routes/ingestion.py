from unittest import result

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


from document_rag_prototype.db.models import Chunk, Document, KnowledgeBase
from document_rag_prototype.db.session import get_db_session
from document_rag_prototype.services.embedding_service import embed_texts
from document_rag_prototype.services.ingestion_service import (
    extract_text_from_file,
    split_text_into_chunks,
)
from document_rag_prototype.services.storage_service import storage_service

router = APIRouter(tags=["Ingestion"])


@router.post("/documents/{document_id}/ingest")
async def ingest_document(
    document_id: int,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
    select(Document)
    .join(KnowledgeBase)
    .where(
        Document.id == document_id,
        KnowledgeBase.workspace_id == x_workspace_id,
    )
)

    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )



    try:
        file_content = await storage_service.read_file(
    document.storage_key or document.filename
    )
        pages = extract_text_from_file(
    file_content=file_content,
    filename=document.filename,
)
        chunk_payloads = split_text_into_chunks(pages)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}",
        ) from exc

    if not chunk_payloads:
        raise HTTPException(
            status_code=400,
            detail="No extractable text found in the document.",
        )

    await db.execute(
        delete(Chunk).where(Chunk.document_id == document_id)
    )

    chunks = [
        Chunk(
            document_id=document_id,
            chunk_index=item["chunk_index"],
            content=item["content"],
            page_number=item["page_number"],
        )
        for item in chunk_payloads
    ]

    db.add_all(chunks)

    await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(status="ingested")
    )

    await db.commit()

    return {
        "document_id": document_id,
        "filename": document.filename,
        "status": "ingested",
        "chunks_created": len(chunks),
    }


@router.post("/documents/{document_id}/embed")
async def embed_document_chunks(
    document_id: int,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
    select(Document)
    .join(KnowledgeBase)
    .where(
        Document.id == document_id,
        KnowledgeBase.workspace_id == x_workspace_id,
    )
)

    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )

    chunks = result.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No chunks found for this document. Ingest the document first.",
        )

    texts = [chunk.content for chunk in chunks]
    embeddings = embed_texts(texts)

    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    await db.commit()

    return {
        "document_id": document_id,
        "filename": document.filename,
        "chunks_embedded": len(chunks),
        "embedding_dimension": len(embeddings[0]) if embeddings else 0,
        "embedding_model": "text-embedding-3-small",
    }
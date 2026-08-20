from pathlib import Path
from unittest import result
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from document_rag_prototype.services.storage_service import storage_service

from document_rag_prototype.api.schemas.models import (
    ChunkCreate,
    ChunkRead,
    DocumentCreate,
    DocumentRead,
)

from document_rag_prototype.db.models import Chunk, Document, KnowledgeBase
from document_rag_prototype.db.session import get_db_session


router = APIRouter(tags=["Documents"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/upload",
    response_model=DocumentRead,
)
async def upload_document(
    knowledge_base_id: int,
    file: UploadFile = File(...),
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
    select(KnowledgeBase).where(
        KnowledgeBase.id == knowledge_base_id,
        KnowledgeBase.workspace_id == x_workspace_id,
    )
)

    knowledge_base = result.scalar_one_or_none()

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have a filename.",
        )

    allowed_extensions = {".pdf", ".txt"}
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported for now.",
        )

    storage_key = (
    f"workspaces/{x_workspace_id}/"
    f"knowledge-bases/{knowledge_base_id}/"
    f"{uuid4()}/{file.filename}"
    )

    saved_path = await storage_service.save_file(
    file=file,
    filename=storage_key,
    )

    document = Document(
    knowledge_base_id=knowledge_base_id,
    filename=file.filename,
    storage_key=storage_key,
    source_type="file",
    status="uploaded",
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


@router.post("/documents", response_model=DocumentRead)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db_session),
):
    knowledge_base = await db.get(
        KnowledgeBase,
        payload.knowledge_base_id,
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found.",
        )

    document = Document(
        knowledge_base_id=payload.knowledge_base_id,
        filename=payload.filename,
        source_type=payload.source_type,
        status=payload.status,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document


@router.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    knowledge_base_id: int,
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(Document)
        .join(KnowledgeBase)
        .where(
            KnowledgeBase.workspace_id == x_workspace_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        .order_by(Document.id)
    )

    return result.scalars().all()

@router.post("/chunks", response_model=ChunkRead)
async def create_chunk(
    payload: ChunkCreate,
    db: AsyncSession = Depends(get_db_session),
):
    document = await db.get(Document, payload.document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    chunk = Chunk(
        document_id=payload.document_id,
        chunk_index=payload.chunk_index,
        content=payload.content,
        page_number=payload.page_number,
    )

    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)

    return chunk


@router.get("/chunks", response_model=list[ChunkRead])
async def list_chunks(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(Chunk).order_by(Chunk.id))
    return result.scalars().all()
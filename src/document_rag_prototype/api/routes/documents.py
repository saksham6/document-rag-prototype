from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.api.schemas.models import (
    DocumentCreate,
    DocumentRead,
)
from document_rag_prototype.core.config import UPLOAD_FOLDER
from document_rag_prototype.db.models import Document, KnowledgeBase
from document_rag_prototype.db.session import get_db_session


router = APIRouter(tags=["Documents"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents/upload",
    response_model=DocumentRead,
)
async def upload_document(
    knowledge_base_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    knowledge_base = await db.get(KnowledgeBase, knowledge_base_id)

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

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_FOLDER / file.filename

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        filename=file.filename,
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
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(Document).order_by(Document.id)
    )
    return result.scalars().all()
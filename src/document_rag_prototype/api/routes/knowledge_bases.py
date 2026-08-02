from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.api.schemas.models import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
)
from document_rag_prototype.db.models import KnowledgeBase
from document_rag_prototype.db.session import get_db_session


router = APIRouter(tags=["Knowledge Bases"])


@router.post("/knowledge-bases", response_model=KnowledgeBaseRead)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db_session),
):
    knowledge_base = KnowledgeBase(
        name=payload.name,
        description=payload.description,
    )

    db.add(knowledge_base)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A knowledge base with this name already exists.",
        ) from exc

    await db.refresh(knowledge_base)
    return knowledge_base


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(KnowledgeBase).order_by(KnowledgeBase.id)
    )
    return result.scalars().all()
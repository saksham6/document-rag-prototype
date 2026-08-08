from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.db.session import get_db_session


router = APIRouter(tags=["Health"])


@router.get("/")
def root() -> dict:
    return {
        "message": "Document RAG Prototype API is running.",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/db-check")
async def db_check(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    result = await db.execute(text("SELECT 1"))
    value = result.scalar_one()

    return {
        "status": "ok",
        "database": "connected",
        "result": value,
        "driver": "sqlalchemy+asyncpg",
    }
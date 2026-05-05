from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.db.models import Chunk, Document, KnowledgeBase
from document_rag_prototype.db.schemas import (
    ChunkCreate,
    ChunkRead,
    DocumentCreate,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
)
from document_rag_prototype.db.session import get_db_session


app = FastAPI(
    title="Document RAG Prototype API",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    source_filter: str | None = Field(default=None, description="Optional exact file name")


class SourceItem(BaseModel):
    source: str
    page: int | None = None
    chunk_id: int
    content_type: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    query_type: str
    query_scope: str
    sources: list[SourceItem]


@app.get("/")
def root() -> dict:
    return {
        "message": "Document RAG Prototype API is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    value = result.scalar_one()

    return {
        "status": "ok",
        "database": "connected",
        "result": value,
        "driver": "sqlalchemy+asyncpg",
    }


@app.post("/knowledge-bases", response_model=KnowledgeBaseRead)
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


@app.get("/knowledge-bases", response_model=list[KnowledgeBaseRead])
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.id))
    return result.scalars().all()


@app.post("/documents", response_model=DocumentRead)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db_session),
):
    knowledge_base = await db.get(KnowledgeBase, payload.knowledge_base_id)

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


@app.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(Document).order_by(Document.id))
    return result.scalars().all()


@app.post("/chunks", response_model=ChunkRead)
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


@app.get("/chunks", response_model=list[ChunkRead])
async def list_chunks(
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(Chunk).order_by(Chunk.id))
    return result.scalars().all()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    source_filter = request.source_filter.strip() if request.source_filter else None

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        from document_rag_prototype.pipeline import run_pipeline

        output = run_pipeline(
            query=question,
            source_filter=source_filter,
            debug=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc

    query_info = output.get("query_info", {})
    results = output.get("results", [])

    sources = [
        SourceItem(
            source=item["source"],
            page=item.get("page"),
            chunk_id=item["chunk_id"],
            content_type=item.get("content_type"),
        )
        for item in results
    ]

    return AskResponse(
        question=output.get("query", question),
        answer=output.get("answer", ""),
        query_type=query_info.get("query_type", "general"),
        query_scope=query_info.get("query_scope", "broad"),
        sources=sources,
    )
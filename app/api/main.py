from pathlib import Path
import shutil
from fastapi.staticfiles import StaticFiles
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from document_rag_prototype.core.config import UPLOAD_FOLDER
from document_rag_prototype.services.ingestion_service import (
    extract_text_from_file,
    split_text_into_chunks,
)
from document_rag_prototype.db.models import Chunk, Document, KnowledgeBase

from document_rag_prototype.api.schemas.models import (
    ChunkCreate,
    ChunkRead,
    DocumentCreate,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    SearchAnswerResponse,
    SearchAnswerSource,
    SearchRequest,
    SearchResult,
)
from document_rag_prototype.db.session import get_db_session
from document_rag_prototype.services.embedding_service import embed_texts

from document_rag_prototype.services.generation_service import generate_answer
from document_rag_prototype.services.retrieval_service import retrieve_chunks
from document_rag_prototype.api.routes.health import router as health_router




app = FastAPI(
    title="Document RAG Prototype API",
    version="0.1.0",
)

app.include_router(health_router)

app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


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


# @app.get("/")
# def root() -> dict:
#     return {
#         "message": "Document RAG Prototype API is running.",
#         "docs": "/docs",
#         "health": "/health",
#     }


# @app.get("/health")
# def health() -> dict:
#     return {"status": "ok"}


# @app.get("/db-check")
# async def db_check(db: AsyncSession = Depends(get_db_session)):
#     result = await db.execute(text("SELECT 1"))
#     value = result.scalar_one()

#     return {
#         "status": "ok",
#         "database": "connected",
#         "result": value,
#         "driver": "sqlalchemy+asyncpg",
#     }


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


@app.post(
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


@app.post("/documents/{document_id}/ingest")
async def ingest_document(
    document_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    document = await db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    file_path = UPLOAD_FOLDER / document.filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Uploaded file not found: {document.filename}",
        )

    try:
        pages = extract_text_from_file(file_path)
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

    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))

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
        "status": document.status,
        "chunks_created": len(chunks),
    }



@app.post("/documents/{document_id}/embed")
async def embed_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    document = await db.get(Document, document_id)

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




class SearchAnswerSource(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    page_number: int | None = None
    distance: float


class SearchAnswerResponse(BaseModel):
    query: str
    answer: str
    sources: list[SearchAnswerSource]




@app.post("/search", response_model=SearchAnswerResponse)
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




# @app.post("/search", response_model=list[SearchResult])
# async def semantic_search(
#     payload: SearchRequest,
#     db: AsyncSession = Depends(get_db_session),
# ):
#     query = payload.query.strip()

#     if not query:
#         raise HTTPException(
#             status_code=400,
#             detail="Search query cannot be empty.",
#         )

#     top_k = max(1, min(payload.top_k, 20))
#     query_embedding = embed_texts([query])[0]
#     query_embedding_str = "[" + ",".join(str(value) for value in query_embedding) + "]"

#     sql = """
#         SELECT
#             chunks.id AS chunk_id,
#             chunks.document_id AS document_id,
#             documents.filename AS filename,
#             chunks.chunk_index AS chunk_index,
#             chunks.page_number AS page_number,
#             chunks.content AS content,
#             chunks.embedding <=> CAST(:query_embedding AS vector) AS distance
#         FROM chunks
#         JOIN documents ON documents.id = chunks.document_id
#         WHERE chunks.embedding IS NOT NULL
#     """

#     params = {
#     "query_embedding": query_embedding_str,
#     "top_k": top_k,
# }

#     if payload.knowledge_base_id is not None:
#         sql += " AND documents.knowledge_base_id = :knowledge_base_id"
#         params["knowledge_base_id"] = payload.knowledge_base_id

#     if payload.document_id is not None:
#         sql += " AND chunks.document_id = :document_id"
#         params["document_id"] = payload.document_id

#     sql += """
#         ORDER BY distance ASC
#         LIMIT :top_k
#     """

#     result = await db.execute(text(sql), params)
#     rows = result.mappings().all()

#     return [
#         SearchResult(
#             chunk_id=row["chunk_id"],
#             document_id=row["document_id"],
#             filename=row["filename"],
#             chunk_index=row["chunk_index"],
#             page_number=row["page_number"],
#             content=row["content"],
#             distance=float(row["distance"]),
#         )
#         for row in rows
#     ]




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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import psycopg


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
def db_check() -> dict:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not set.")

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()

        return {
            "status": "ok",
            "database_connected": True,
            "result": result[0],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc


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
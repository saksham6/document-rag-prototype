from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from document_rag_prototype.api.routes.documents import router as documents_router
from document_rag_prototype.api.routes.health import router as health_router
from document_rag_prototype.api.routes.ingestion import router as ingestion_router
from document_rag_prototype.api.routes.knowledge_bases import (
    router as knowledge_bases_router,
)
from document_rag_prototype.api.routes.rag import router as rag_router


app = FastAPI(
    title="Document RAG Prototype API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(knowledge_bases_router)
app.include_router(documents_router)
app.include_router(ingestion_router)
app.include_router(rag_router)

app.mount(
    "/ui",
    StaticFiles(directory="static", html=True),
    name="ui",
)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class DocumentCreate(BaseModel):
    knowledge_base_id: int
    filename: str
    source_type: str = "file"
    status: str = "uploaded"


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    filename: str
    source_type: str
    status: str
    created_at: datetime


class ChunkCreate(BaseModel):
    document_id: int
    chunk_index: int
    content: str
    page_number: Optional[int] = None


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_index: int
    content: str
    page_number: Optional[int]
    created_at: datetime
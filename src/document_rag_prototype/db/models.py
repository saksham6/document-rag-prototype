from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="file")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        back_populates="documents",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        back_populates="chunks",
    )
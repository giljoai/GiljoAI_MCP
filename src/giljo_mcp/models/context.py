"""
MCP Context Index model for GiljoAI MCP.

Stores chunked vision documents for agentic RAG with PostgreSQL full-text search.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class MCPContextIndex(Base):
    """
    MCP Context Index model - stores chunked vision documents for agentic RAG.

    Handover 0017: Enables full-text search on vision document chunks for context prioritization.
    Chunks are created by EnhancedChunker from vision_document or vision_path content.

    Multi-tenant isolation: All queries filter by tenant_key.
    """

    __tablename__ = "mcp_context_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    chunk_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)

    # Handover 0043: Multi-Vision Document Support
    vision_document_id = Column(
        String(36),
        ForeignKey("vision_documents.id", ondelete="CASCADE"),
        nullable=True,
        comment="Link to specific vision document (NULL for legacy product-level chunks)",
    )
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True, comment="Optional LLM-generated summary (NULL for Phase 1 non-LLM chunking)")
    keywords = Column(JSONB, default=list, comment="Array of keyword strings extracted via regex or LLM")
    token_count = Column(Integer, nullable=True)
    chunk_order = Column(Integer, nullable=True, comment="Sequential chunk number for maintaining document order")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # PostgreSQL full-text search (requires pg_trgm extension)
    searchable_vector = Column(TSVECTOR, nullable=True, comment="Full-text search vector for fast keyword lookup")

    # Relationships
    product = relationship("Product", backref="context_chunks")
    vision_document = relationship("VisionDocument", back_populates="chunks", foreign_keys=[vision_document_id])

    __table_args__ = (
        Index("idx_mcp_context_tenant_product", "tenant_key", "product_id"),
        Index("idx_mcp_context_searchable", "searchable_vector", postgresql_using="gin"),
        Index("idx_mcp_context_chunk_id", "chunk_id"),
        # Handover 0043: Vision document indexes
        Index("idx_mcp_context_vision_doc", "vision_document_id"),
        Index("idx_mcp_context_product_vision_doc", "product_id", "vision_document_id"),
    )

    def __repr__(self) -> str:
        return f"<MCPContextIndex(id={self.id}, chunk_id={self.chunk_id}, product_id={self.product_id})>"

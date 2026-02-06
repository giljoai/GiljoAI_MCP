"""
Context and indexing-related models for GiljoAI MCP.

This module contains models for context indexing, large document tracking,
and MCP context management. These models support RAG (Retrieval-Augmented Generation)
and efficient context management for agents.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class ContextIndex(Base):
    """
    Context Index model - provides fast navigation for chunked documents.
    Enables O(1) chunk retrieval and document discovery.
    """

    __tablename__ = "context_index"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    index_type = Column(String(50), nullable=False)  # vision, document, session
    document_name = Column(String(255), nullable=False)
    section_name = Column(String(255), nullable=True)
    chunk_numbers = Column(JSON, default=list)  # Array of chunk numbers this appears in
    summary = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=True)
    keywords = Column(JSON, default=list)  # Array of keywords
    full_path = Column(Text, nullable=True)
    content_hash = Column(String(32), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="context_indexes")

    __table_args__ = (
        UniqueConstraint("project_id", "document_name", "section_name", name="uq_context_index"),
        Index("idx_context_tenant", "tenant_key"),
        Index("idx_context_type", "index_type"),
        Index("idx_context_doc", "document_name"),
    )

    def __repr__(self) -> str:
        return f"<ContextIndex(id={self.id}, document_name='{self.document_name}')>"


class LargeDocumentIndex(Base):
    """
    Large Document Index model - tracks documents requiring chunking.
    Provides metadata and navigation for documents over 50K tokens.
    """

    __tablename__ = "large_document_index"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    document_path = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=True)  # markdown, yaml, text
    total_size = Column(Integer, nullable=True)  # Total characters
    total_tokens = Column(Integer, nullable=True)  # Estimated total tokens
    chunk_count = Column(Integer, nullable=True)
    meta_data = Column(JSON, default=dict)  # Changed from metadata to avoid SQLAlchemy conflict
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="document_indexes")

    __table_args__ = (
        UniqueConstraint("project_id", "document_path", name="uq_large_doc_path"),
        Index("idx_large_doc_tenant", "tenant_key"),
    )

    def __repr__(self) -> str:
        return f"<LargeDocumentIndex(id={self.id}, document_path='{self.document_path}')>"


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
    keywords = Column(JSON, default=list, comment="Array of keyword strings extracted via regex or LLM")
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


class MCPContextSummary(Base):
    """
    MCP Context Summary model - tracks orchestrator-created condensed missions.

    Handover 0017: Enables context prioritization and orchestration by condensing full context into missions.
    Orchestrator creates condensed versions of vision chunks for agent spawning.

    Multi-tenant isolation: All queries filter by tenant_key.
    """

    __tablename__ = "mcp_context_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    context_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    full_content = Column(Text, nullable=False, comment="Original full context before condensation")
    condensed_mission = Column(Text, nullable=False, comment="Orchestrator-generated condensed mission")
    full_token_count = Column(Integer, nullable=True)
    condensed_token_count = Column(Integer, nullable=True)
    reduction_percent = Column(Float, nullable=True, comment="Context prioritization percentage achieved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", backref="context_summaries")

    __table_args__ = (
        Index("idx_mcp_summary_tenant_product", "tenant_key", "product_id"),
        Index("idx_mcp_summary_context_id", "context_id"),
    )

    def __repr__(self) -> str:
        return f"<MCPContextSummary(id={self.id}, context_id={self.context_id}, reduction={self.reduction_percent}%)>"

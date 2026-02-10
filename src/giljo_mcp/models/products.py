"""
Product-related models for GiljoAI MCP.

This module contains models for products, vision documents, and vision chunks.
Products are the top-level organizational unit in the system.
"""

from typing import Any

from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class Product(Base):
    """
    Product model - TOP-level organizational unit.
    All projects, tasks, and agents belong to a product.

    Vision Storage (Handover 0017 - Hybrid Approach):
    - vision_path: File-based storage (existing workflow)
    - vision_document: Inline text storage (new agentic workflow)
    - vision_type: Source type ('file', 'inline', 'none')
    - chunked: Has vision been chunked into mcp_context_index

    Handover 0316: Added quality_standards field for testing expectations.
    """

    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Organization that owns this product (Handover 0424)",
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Handover 0084: Project path for agent export (required for copy-command interface)
    project_path = Column(
        String(500), nullable=True, comment="File system path to product folder (required for agent export)"
    )

    # Handover 0316: Quality standards for testing expectations
    quality_standards = Column(Text, nullable=True, comment="Quality standards and testing expectations")

    # Handover 0425: Target platforms for product deployment
    target_platforms = Column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{all}'::text[]"),
        comment="Target platforms: windows, linux, macos, or all",
    )

    # ✅ Handover 0128e Complete: Deprecated vision fields removed
    # Migration completed - all production code now uses VisionDocument relationship.
    # Use these helper properties instead:
    #    - product.vision_documents (VisionDocument relationship)
    #    - product.primary_vision_text (helper property)
    #    - product.primary_vision_path (helper property)
    #    - product.has_vision (helper property)
    #    - product.vision_is_chunked (helper property)
    #    - product.primary_vision_storage_type (helper property)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when product was soft deleted (NULL for active products)",
    )
    meta_data = Column(JSON, default=dict)

    # Product status (Handover 0049)
    is_active = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Active product for token estimation and mission planning (one per tenant)",
    )

    # Rich configuration data (JSONB for PostgreSQL performance)
    config_data = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Rich project configuration: architecture, tech_stack, features, etc.",
    )

    # 360 Memory Management storage (Handover 0135, updated 0700c)
    # Note: sequential_history removed in 0700c - use product_memory_entries table
    product_memory = Column(
        JSONB,
        nullable=False,
        server_default=text('\'{"github": {}, "context": {}}\'::jsonb'),
        comment="Product memory config storage. Contains git_integration settings only.",
    )

    # Consolidated vision summaries (Handover 0377)
    # These store pre-computed summaries aggregated from ALL active vision documents
    consolidated_vision_light = Column(
        Text, nullable=True, comment="33% summary of all active vision documents (consolidated)"
    )
    consolidated_vision_light_tokens = Column(
        Integer, nullable=True, comment="Token count of consolidated light summary"
    )
    consolidated_vision_medium = Column(
        Text, nullable=True, comment="66% summary of all active vision documents (consolidated)"
    )
    consolidated_vision_medium_tokens = Column(
        Integer, nullable=True, comment="Token count of consolidated medium summary"
    )
    consolidated_vision_hash = Column(
        String(64), nullable=True, comment="SHA-256 hash of aggregated vision documents (for change detection)"
    )
    consolidated_at = Column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when consolidated summaries were last generated"
    )

    # Relationships
    organization = relationship("Organization", back_populates="products")
    projects = relationship("Project", back_populates="product", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="product", cascade="all, delete-orphan")

    # Handover 0043: Multi-Vision Document Support
    vision_documents = relationship(
        "VisionDocument",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="VisionDocument.display_order",
    )

    # Handover 0390a: 360 Memory Entries
    memory_entries = relationship("ProductMemoryEntry", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_tenant", "tenant_key"),
        Index("idx_product_org_id", "org_id"),
        Index("idx_product_name", "name"),
        Index("idx_product_config_data_gin", "config_data", postgresql_using="gin"),  # GIN index for JSONB
        Index(
            "idx_product_memory_gin", "product_memory", postgresql_using="gin"
        ),  # Handover 0135: GIN index for product_memory
        Index(
            "idx_products_deleted_at", "deleted_at", postgresql_where=text("deleted_at IS NOT NULL")
        ),  # Soft delete support
        Index("idx_products_consolidated_at", "consolidated_at"),  # Handover 0377: Consolidated vision index
        # Handover 0128e: Removed CheckConstraint for deprecated vision_type field
        # Handover 0425: Validate target_platforms field
        CheckConstraint(
            "target_platforms <@ ARRAY['windows', 'linux', 'macos', 'all']::VARCHAR[]",
            name="ck_product_target_platforms_valid",
        ),
        CheckConstraint(
            "NOT ('all' = ANY(target_platforms) AND array_length(target_platforms, 1) > 1)",
            name="ck_product_target_platforms_all_exclusive",
        ),
        # Handover 0050: Enforce single active product per tenant (defense in depth)
        Index(
            "idx_product_single_active_per_tenant", "tenant_key", unique=True, postgresql_where=text("is_active = true")
        ),
    )

    @property
    def has_config_data(self) -> bool:
        """Check if product has config_data populated"""
        return bool(self.config_data and len(self.config_data) > 0)

    def get_config_field(self, field_path: str, default: Any = None) -> Any:
        """
        Get config field using dot notation (e.g., 'tech_stack.python')

        Args:
            field_path: Dot-separated path (e.g., 'architecture' or 'test_config.coverage')
            default: Default value if field not found

        Returns:
            Field value or default
        """
        if not self.config_data:
            return default

        keys = field_path.split(".")
        value = self.config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    # Handover 0135: Product Memory helper methods
    @property
    def has_product_memory(self) -> bool:
        """Check if product has product_memory populated beyond defaults"""
        if not self.product_memory:
            return False
        # Consider it populated if any top-level key has data beyond empty defaults
        # Note: sequential_history moved to product_memory_entries table (0700c)
        has_github = bool(self.product_memory.get("github", {}))
        has_context = bool(self.product_memory.get("context", {}))
        return has_github or has_context

    def get_memory_field(self, field_path: str, default: Any = None) -> Any:
        """
        Get memory field using dot notation (e.g., 'github.enabled')

        Args:
            field_path: Dot-separated path (e.g., 'github.enabled' or 'context.summary')
            default: Default value if field not found

        Returns:
            Field value or default

        Examples:
            >>> product.get_memory_field('github.enabled')
            True
            >>> product.get_memory_field('github.repo_url')
            'https://github.com/user/repo'
            >>> product.get_memory_field('context.summary')
            'A product management system'
        """
        if not self.product_memory:
            return default

        keys = field_path.split(".")
        value = self.product_memory

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    # Handover 0043: Vision Documents properties
    @property
    def has_vision_documents(self) -> bool:
        """Check if product has any active vision documents"""
        if not hasattr(self, "vision_documents") or not self.vision_documents:
            return False
        return any(doc.is_active for doc in self.vision_documents)

    @property
    def all_documents_chunked(self) -> bool:
        """Check if all active vision documents have been chunked"""
        if not self.has_vision_documents:
            return False
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        if not active_docs:
            return False
        return all(doc.chunked for doc in active_docs)

    # Handover 0128e: Migration helper properties (replaces deprecated fields)
    @property
    def primary_vision_text(self) -> str:
        """
        Get primary vision document text.
        Replaces deprecated: product.vision_document field
        """
        if not self.vision_documents:
            return ""
        # Get first active document, or first document if none active
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        doc = active_docs[0] if active_docs else (self.vision_documents[0] if self.vision_documents else None)
        if not doc:
            return ""
        return doc.vision_document or ""

    @property
    def primary_vision_path(self) -> str:
        """
        Get primary vision file path.
        Replaces deprecated: product.vision_path field
        """
        if not self.vision_documents:
            return ""
        # Get first active document, or first document if none active
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        doc = active_docs[0] if active_docs else (self.vision_documents[0] if self.vision_documents else None)
        if not doc:
            return ""
        return doc.vision_path or ""

    @property
    def has_vision(self) -> bool:
        """
        Check if product has vision content.
        Replaces deprecated: bool(product.vision_document) checks
        """
        if not self.vision_documents:
            return False
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        docs_to_check = active_docs if active_docs else self.vision_documents
        return any((doc.vision_document or doc.vision_path) for doc in docs_to_check)

    @property
    def vision_is_chunked(self) -> bool:
        """
        Check if vision is chunked.
        Replaces deprecated: product.chunked field
        """
        if not self.vision_documents:
            return False
        # Get first active document, or first document if none active
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        doc = active_docs[0] if active_docs else (self.vision_documents[0] if self.vision_documents else None)
        if not doc:
            return False
        return doc.chunked

    @property
    def primary_vision_storage_type(self) -> str:
        """
        Get primary vision storage type.
        Replaces deprecated: product.vision_type field
        """
        if not self.vision_documents:
            return "none"
        # Get first active document, or first document if none active
        active_docs = [doc for doc in self.vision_documents if doc.is_active]
        doc = active_docs[0] if active_docs else (self.vision_documents[0] if self.vision_documents else None)
        if not doc:
            return "none"
        return doc.storage_type

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', tenant_key='{self.tenant_key}')>"


class VisionDocument(Base):
    """
    Vision Document model - stores multiple vision documents per product.

    Handover 0043: Multi-Vision Document Support - Phase 1
    Enables products to have multiple vision documents (architecture, features, setup, etc.)
    with chunking, versioning, and flexible storage (file-based or inline).

    Storage Types:
    - 'file': vision_path points to file, vision_document is NULL
    - 'inline': vision_document contains text, vision_path is NULL
    - 'hybrid': Both vision_path and vision_document populated (file + inline)

    Document Types:
    - 'vision': Primary vision document
    - 'architecture': Architecture/design documents
    - 'features': Feature specifications
    - 'setup': Setup/installation guides
    - 'api': API documentation
    - 'testing': Test plans and strategies
    - 'deployment': Deployment guides
    - 'custom': User-defined document types

    Multi-tenant isolation: All queries filter by tenant_key.
    CASCADE deletes: Deleting VisionDocument deletes all chunks (via MCPContextIndex).
    """

    __tablename__ = "vision_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Document identification
    document_name = Column(
        String(255), nullable=False, comment="User-friendly document name (e.g., 'Product Architecture', 'API Design')"
    )
    document_type = Column(
        String(50),
        nullable=False,
        default="vision",
        comment="Document category: vision, architecture, features, setup, api, testing, deployment, custom",
    )

    # Storage configuration (flexible: file, inline, or hybrid)
    vision_path = Column(
        String(500), nullable=True, comment="File path to vision document (file-based or hybrid storage)"
    )
    vision_document = Column(Text, nullable=True, comment="Inline vision text (inline or hybrid storage)")
    storage_type = Column(
        String(20), nullable=False, default="file", comment="Storage mode: 'file', 'inline', or 'hybrid'"
    )

    # Chunking state
    chunked = Column(
        Boolean, default=False, nullable=False, comment="Has document been chunked into mcp_context_index for RAG"
    )
    chunk_count = Column(Integer, default=0, nullable=False, comment="Number of chunks created for this document")
    total_tokens = Column(Integer, nullable=True, comment="Estimated total tokens in document")
    file_size = Column(
        BigInteger, nullable=True, comment="Original file size in bytes (NULL for inline content without file)"
    )

    # Summarization metadata (Handover 0345b, enhanced in 0345e, cleaned in 0374)
    is_summarized = Column(
        Boolean, default=False, nullable=False, comment="Has document been summarized using LSA algorithm"
    )
    original_token_count = Column(Integer, nullable=True, comment="Original document token count before summarization")

    # Multi-level summaries (Handover 0345e, simplified in 0246b, cleaned in 0374)
    # Handover 0374: 3-tier system (light=33%, medium=66%, full=original)
    summary_light = Column(Text, nullable=True, comment="Light summary (~33% of original, ~13K tokens for 40K doc)")
    summary_medium = Column(Text, nullable=True, comment="Medium summary (~66% of original, ~26K tokens for 40K doc)")
    summary_light_tokens = Column(Integer, nullable=True, comment="Actual token count in light summary")
    summary_medium_tokens = Column(Integer, nullable=True, comment="Actual token count in medium summary")

    # Versioning and integrity
    version = Column(String(50), default="1.0.0", nullable=False, comment="Document version using semantic versioning")
    content_hash = Column(String(64), nullable=True, comment="SHA-256 hash of document content for change detection")

    # Status and display
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Active documents are used for context; inactive are archived"
    )
    display_order = Column(Integer, default=0, nullable=False, comment="Display order in UI (lower numbers first)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Additional metadata
    meta_data = Column(JSON, default=dict, comment="Additional metadata: author, tags, source_url, etc.")

    # Relationships
    product = relationship("Product", back_populates="vision_documents")
    chunks = relationship(
        "MCPContextIndex",
        back_populates="vision_document",
        cascade="all, delete-orphan",
        foreign_keys="MCPContextIndex.vision_document_id",
    )

    __table_args__ = (
        # Unique constraint: one document name per product
        UniqueConstraint("product_id", "document_name", name="uq_vision_doc_product_name"),
        # Multi-tenant isolation index (PRIMARY)
        Index("idx_vision_doc_tenant", "tenant_key"),
        Index("idx_vision_doc_product", "product_id"),
        # Query optimization indexes
        Index("idx_vision_doc_type", "document_type"),
        Index("idx_vision_doc_active", "is_active"),
        Index("idx_vision_doc_chunked", "chunked"),
        # Composite indexes for common queries
        Index("idx_vision_doc_tenant_product", "tenant_key", "product_id"),
        Index("idx_vision_doc_product_type", "product_id", "document_type"),
        Index("idx_vision_doc_product_active", "product_id", "is_active", "display_order"),
        # Storage type constraint
        CheckConstraint("storage_type IN ('file', 'inline', 'hybrid')", name="ck_vision_doc_storage_type"),
        # Document type constraint
        CheckConstraint(
            "document_type IN ('vision', 'architecture', 'features', 'setup', 'api', 'testing', 'deployment', 'custom')",
            name="ck_vision_doc_document_type",
        ),
        # Storage consistency constraints
        CheckConstraint(
            "(storage_type = 'file' AND vision_path IS NOT NULL) OR "
            "(storage_type = 'inline' AND vision_document IS NOT NULL) OR "
            "(storage_type = 'hybrid' AND vision_path IS NOT NULL AND vision_document IS NOT NULL)",
            name="ck_vision_doc_storage_consistency",
        ),
        # Chunk count consistency
        CheckConstraint("chunk_count >= 0", name="ck_vision_doc_chunk_count"),
        CheckConstraint(
            "(chunked = false AND chunk_count = 0) OR (chunked = true AND chunk_count > 0)",
            name="ck_vision_doc_chunked_consistency",
        ),
    )

    @property
    def needs_rechunking(self) -> bool:
        """
        Check if document needs rechunking based on content changes.

        Returns:
            True if content_hash is None or content has changed since last chunking
        """
        if not self.chunked:
            return True

        if self.content_hash is None:
            return True

        # Calculate current content hash
        import hashlib

        content = ""

        if self.storage_type == "file" and self.vision_path:
            try:
                from pathlib import Path

                path = Path(self.vision_path)
                if path.exists():
                    content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return True
        elif self.storage_type == "inline" and self.vision_document:
            content = self.vision_document
        elif self.storage_type == "hybrid":
            # For hybrid, combine both sources
            if self.vision_path:
                try:
                    from pathlib import Path

                    path = Path(self.vision_path)
                    if path.exists():
                        content += path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    pass  # nosec B110 - file read fallback
            if self.vision_document:
                content += self.vision_document

        current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return current_hash != self.content_hash

    def update_content_hash(self) -> str:
        """
        Update content_hash based on current content.

        Returns:
            The new content hash (SHA-256)
        """
        import hashlib

        content = ""

        if self.storage_type == "file" and self.vision_path:
            try:
                from pathlib import Path

                path = Path(self.vision_path)
                if path.exists():
                    content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass  # nosec B110 - file read fallback
        elif self.storage_type == "inline" and self.vision_document:
            content = self.vision_document
        elif self.storage_type == "hybrid":
            # For hybrid, combine both sources
            if self.vision_path:
                try:
                    from pathlib import Path

                    path = Path(self.vision_path)
                    if path.exists():
                        content += path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    pass  # nosec B110 - file read fallback
            if self.vision_document:
                content += self.vision_document

        self.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return self.content_hash

    def __repr__(self) -> str:
        return f"<VisionDocument(id={self.id}, name='{self.document_name}', product_id='{self.product_id}')>"

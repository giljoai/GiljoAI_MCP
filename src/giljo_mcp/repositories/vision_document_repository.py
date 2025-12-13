"""
Vision Document Repository for managing multi-vision document support.

Handover 0043 Phase 2: Repository layer for VisionDocument CRUD operations.
Implements tenant-isolated database operations with automatic content hashing.

All operations enforce tenant_key filtering for security (zero cross-tenant leakage).
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import DatabaseManager
from ..models import MCPContextIndex, Product, VisionDocument
from .base import BaseRepository


class VisionDocumentRepository:
    """
    Repository for VisionDocument operations with multi-tenant isolation.

    Handles vision document CRUD operations with automatic:
    - Content hashing (SHA-256) for change detection
    - Timestamp management (created_at, updated_at, chunked_at)
    - Tenant isolation (CRITICAL security)
    - Display order management
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize vision document repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.base_repo = BaseRepository(VisionDocument, db_manager)

    async def create(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
        document_name: str,
        content: str,
        document_type: str = "vision",
        storage_type: str = "inline",
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        is_active: bool = True,
        display_order: int = 0,
        version: str = "1.0.0",
        meta_data: Optional[Dict] = None,
    ) -> VisionDocument:
        """
        Create a new vision document with automatic content hashing.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation (CRITICAL)
            product_id: Product this document belongs to
            document_name: User-friendly document name
            content: Document content (inline or from file)
            document_type: Document category (vision, architecture, features, etc.)
            storage_type: Storage mode (file, inline, hybrid)
            file_path: Optional file path for file-based storage
            file_size: Optional file size in bytes (NULL if inline without file)
            is_active: Whether document is active (default: True)
            display_order: Display order in UI (default: 0)
            version: Semantic version (default: "1.0.0")
            meta_data: Additional metadata dict

        Returns:
            Created VisionDocument instance

        Raises:
            ValueError: If product doesn't exist or belong to tenant
        """
        # Validate product exists and belongs to tenant
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product {product_id} not found for tenant {tenant_key}")

        # Generate content hash (SHA-256)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Create vision document instance
        doc = VisionDocument(
            tenant_key=tenant_key,
            product_id=product_id,
            document_name=document_name,
            vision_document=content,  # Handover 0246b: Always store full content in DB
            vision_path=file_path if storage_type in ("file", "hybrid") else None,
            storage_type=storage_type,
            document_type=document_type,
            content_hash=content_hash,
            file_size=file_size,
            is_active=is_active,
            display_order=display_order,
            version=version,
            chunked=False,
            chunk_count=0,
            meta_data=meta_data or {},
        )

        session.add(doc)
        await session.flush()

        return doc

    async def get_by_id(self, session: AsyncSession, tenant_key: str, document_id: str) -> Optional[VisionDocument]:
        """
        Get vision document by ID with tenant filter (CRITICAL security).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            document_id: Document ID to retrieve

        Returns:
            VisionDocument instance or None if not found
        """
        stmt = select(VisionDocument).where(VisionDocument.id == document_id, VisionDocument.tenant_key == tenant_key)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_product(
        self, session: AsyncSession, tenant_key: str, product_id: str, active_only: bool = True
    ) -> List[VisionDocument]:
        """
        List all vision documents for a product with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to list documents for
            active_only: If True, only return active documents (default: True)

        Returns:
            List of VisionDocument instances ordered by display_order
        """
        stmt = select(VisionDocument).where(
            VisionDocument.tenant_key == tenant_key, VisionDocument.product_id == product_id
        )

        if active_only:
            stmt = stmt.where(VisionDocument.is_active == True)

        stmt = stmt.order_by(VisionDocument.display_order, VisionDocument.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_content(
        self, session: AsyncSession, tenant_key: str, document_id: str, new_content: str
    ) -> Optional[VisionDocument]:
        """
        Update vision document content with automatic hash recalculation and chunked reset.

        When content is updated:
        1. Recalculates content hash (SHA-256)
        2. Resets chunked flag to False (requires re-chunking)
        3. Resets chunk_count to 0
        4. Updates updated_at timestamp

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            document_id: Document ID to update
            new_content: New document content

        Returns:
            Updated VisionDocument instance or None if not found
        """
        doc = await self.get_by_id(session, tenant_key, document_id)

        if not doc:
            return None

        # Update content and recalculate hash
        if doc.storage_type in ("inline", "hybrid"):
            doc.vision_document = new_content

        doc.content_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()

        # Reset chunked status (content changed, needs re-chunking)
        doc.chunked = False
        doc.chunk_count = 0
        doc.total_tokens = None
        doc.chunked_at = None

        # Update timestamp
        doc.updated_at = datetime.now(timezone.utc)

        await session.flush()
        return doc

    async def delete(self, session: AsyncSession, tenant_key: str, document_id: str) -> Dict[str, Any]:
        """
        Delete vision document and all associated chunks.

        Chunks are deleted automatically via CASCADE constraint on vision_document_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            document_id: Document ID to delete

        Returns:
            Dict with success status, document_id, document_name, and chunks_deleted count
        """
        doc = await self.get_by_id(session, tenant_key, document_id)

        if not doc:
            return {"success": False, "message": "Document not found"}

        # Count chunks before deletion (for stats)
        stmt = select(MCPContextIndex).where(
            MCPContextIndex.vision_document_id == document_id, MCPContextIndex.tenant_key == tenant_key
        )
        result = await session.execute(stmt)
        chunk_count = len(result.scalars().all())

        document_name = doc.document_name

        # Delete document (chunks cascade automatically)
        await session.delete(doc)
        await session.flush()

        return {
            "success": True,
            "document_id": document_id,
            "document_name": document_name,
            "chunks_deleted": chunk_count,
        }

    async def mark_chunked(self, session: AsyncSession, document_id: str, chunk_count: int, total_tokens: int) -> None:
        """
        Mark document as chunked with metadata.

        Updates:
        - chunked flag to True
        - chunk_count
        - total_tokens
        - chunked_at timestamp
        - content_hash (ensures hash is current)

        Handover 0047: Converted to async for proper async/await propagation.

        Args:
            session: Async database session
            document_id: Document ID to mark as chunked
            chunk_count: Number of chunks created
            total_tokens: Total estimated tokens in document
        """
        stmt = select(VisionDocument).where(VisionDocument.id == document_id)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc:
            doc.chunked = True
            doc.chunk_count = chunk_count
            doc.total_tokens = total_tokens
            doc.chunked_at = datetime.now(timezone.utc)

            # Ensure content hash is current
            if doc.vision_document:
                doc.content_hash = hashlib.sha256(doc.vision_document.encode("utf-8")).hexdigest()

            await session.flush()

    async def get_by_type(
        self, session: AsyncSession, tenant_key: str, product_id: str, document_type: str
    ) -> List[VisionDocument]:
        """
        Get all vision documents of a specific type for a product.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to search within
            document_type: Document type to filter by (vision, architecture, etc.)

        Returns:
            List of VisionDocument instances
        """
        result = await session.execute(
            select(VisionDocument)
            .where(
                VisionDocument.tenant_key == tenant_key,
                VisionDocument.product_id == product_id,
                VisionDocument.document_type == document_type,
                VisionDocument.is_active == True,
            )
            .order_by(VisionDocument.display_order)
        )
        return list(result.scalars().all())

    async def set_active_status(
        self, session: AsyncSession, tenant_key: str, document_id: str, is_active: bool
    ) -> Optional[VisionDocument]:
        """
        Set active status of a vision document.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            document_id: Document ID to update
            is_active: New active status

        Returns:
            Updated VisionDocument instance or None if not found
        """
        doc = await self.get_by_id(session, tenant_key, document_id)

        if doc:
            doc.is_active = is_active
            doc.updated_at = datetime.now(timezone.utc)
            await session.flush()

        return doc

    async def update_display_order(
        self, session: AsyncSession, tenant_key: str, document_id: str, new_order: int
    ) -> Optional[VisionDocument]:
        """
        Update display order of a vision document.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            document_id: Document ID to update
            new_order: New display order value

        Returns:
            Updated VisionDocument instance or None if not found
        """
        doc = await self.get_by_id(session, tenant_key, document_id)

        if doc:
            doc.display_order = new_order
            doc.updated_at = datetime.now(timezone.utc)
            await session.flush()

        return doc

    async def count_by_product(self, session: AsyncSession, tenant_key: str, product_id: str, active_only: bool = True) -> int:
        """
        Count vision documents for a product.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to count documents for
            active_only: If True, only count active documents (default: True)

        Returns:
            Number of vision documents
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(VisionDocument).where(
            VisionDocument.tenant_key == tenant_key, VisionDocument.product_id == product_id
        )

        if active_only:
            stmt = stmt.where(VisionDocument.is_active == True)

        result = await session.execute(stmt)
        return result.scalar()

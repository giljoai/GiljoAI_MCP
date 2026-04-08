# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductVisionService - Vision document lifecycle management

Handover 0950i: Extracted from ProductService to reduce god-class size.

Responsibilities:
- Vision document upload and storage
- Multi-level summarization trigger
- Auto-chunking of large documents
- Auto-consolidation after upload

Design Principles:
- Single Responsibility: Only vision document lifecycle
- Dependency Injection: Accepts DatabaseManager and tenant_key
- Async/Await: Full SQLAlchemy 2.0 async support
- ProductVisionService may call ProductService to fetch parent Product
- ProductService must NOT import from this module
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ContextError,
    GiljoFileNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import Product
from src.giljo_mcp.schemas.service_responses import VisionUploadResult
from src.giljo_mcp.tools.chunking import VISION_MAX_INGEST_TOKENS


logger = logging.getLogger(__name__)


class ProductVisionService:
    """
    Service for managing vision document lifecycle.

    Handles uploading, summarizing, chunking, and consolidating
    vision documents for products.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_session: AsyncSession | None = None,
    ):
        """
        Initialize ProductVisionService.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    async def upload_vision_document(
        self,
        product_id: str,
        content: str,
        filename: str,
        auto_chunk: bool = True,
        max_tokens: int = VISION_MAX_INGEST_TOKENS,
    ) -> VisionUploadResult:
        """
        Upload and optionally chunk vision document for product.

        Uses VisionDocumentChunker for intelligent chunking at semantic boundaries.
        Documents exceeding max_tokens are automatically split into chunks.

        Args:
            product_id: Product UUID
            content: Document content (text/markdown)
            filename: Document filename
            auto_chunk: Auto-chunk if content exceeds max_tokens (default: True)
            max_tokens: Max tokens per chunk (default: 25000 for 32K models)

        Returns:
            VisionUploadResult Pydantic model with document_id, document_name,
            chunks_created, and total_tokens

        Raises:
            ValidationError: If validation fails
            ResourceNotFoundError: If product not found
            BaseGiljoError: If upload fails

        Example:
            >>> result = await service.upload_vision_document(
            ...     product_id="abc-123",
            ...     content="# Vision\\n...",
            ...     filename="vision.md"
            ... )
            >>> print(f"Created {result.chunks_created} chunks")
        """
        try:
            from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

            async with self._get_session() as session:
                # Verify product exists and belongs to tenant
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message=f"Product {product_id} not found or access denied",
                        context={"product_id": product_id, "tenant_key": self.tenant_key},
                    )

                # Create vision document via repository
                vision_repo = VisionDocumentRepository(db_manager=self.db_manager)

                # Calculate file size
                file_size = len(content.encode("utf-8"))

                # Create document (inline storage)
                doc = await vision_repo.create(
                    session=session,
                    tenant_key=self.tenant_key,
                    product_id=product_id,
                    document_name=filename,
                    content=content,
                    document_type="vision",
                    storage_type="inline",
                    file_size=file_size,
                    is_active=True,
                    display_order=0,
                )

                await session.commit()

                self._logger.info(f"Created vision document {doc.id} for product {product_id}")

                # Multi-level summarization (Handover 0345e)
                total_tokens = len(content) // 4  # Rough estimate: 1 token ~ 4 chars

                if total_tokens > 100:
                    self._summarize_document(session, doc, content, total_tokens)

                # Auto-chunk if enabled
                chunks_created, total_tokens = await self._chunk_document(
                    session, doc, content, auto_chunk, max_tokens, total_tokens
                )

                # Handover 0493: Auto-consolidation after upload
                await self._consolidate_vision(session, product_id)

                return VisionUploadResult(
                    document_id=str(doc.id),
                    document_name=doc.document_name,
                    chunks_created=chunks_created,
                    total_tokens=total_tokens,
                )

        except ValueError as e:
            self._logger.exception("Validation error uploading vision document")
            raise ValidationError(
                message=f"Validation error uploading vision document: {e!s}",
                context={"product_id": product_id, "filename": filename},
            ) from e
        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to upload vision document")
            raise BaseGiljoError(
                message=f"Failed to upload vision document: {e!s}",
                context={"product_id": product_id, "filename": filename, "tenant_key": self.tenant_key},
            ) from e

    def _summarize_document(self, session, doc, content: str, total_tokens: int) -> None:
        """Generate multi-level summaries for a vision document.

        Handover 0345e: Always generate summaries for large documents.
        Handover 0377: Summarize all documents (100 token minimum).

        Args:
            session: Database session (for re-attaching doc)
            doc: VisionDocument ORM instance
            content: Document text content
            total_tokens: Estimated token count
        """
        try:
            from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

            self._logger.info(f"Generating multi-level summaries for doc {doc.id}: {total_tokens} tokens")

            summarizer = VisionDocumentSummarizer()
            summaries = summarizer.summarize_multi_level(content)

            # Re-attach doc to session after previous commit (fixes detached state)
            session.add(doc)

            # Store summary levels (Handover 0352: light and medium only)
            doc.summary_light = summaries.light.summary
            doc.summary_medium = summaries.medium.summary
            doc.summary_light_tokens = summaries.light.tokens
            doc.summary_medium_tokens = summaries.medium.tokens
            doc.is_summarized = True
            doc.original_token_count = summaries.original_tokens

            # Backward compatibility: set summary_text to medium summary
            doc.summary_text = summaries.medium.summary
            doc.compression_ratio = (
                (summaries.original_tokens - summaries.medium.tokens) / summaries.original_tokens
                if summaries.original_tokens > 0
                else 0.0
            )

            self._logger.info(
                f"Vision document {doc.id} summarized: "
                f"Light={summaries.light.tokens} tokens, "
                f"Medium={summaries.medium.tokens} tokens "
                f"(from {summaries.original_tokens} tokens) "
                f"in {summaries.processing_time_ms}ms"
            )
        except (ImportError, ValueError, KeyError) as e:
            # Summarization failed but document created - log warning and continue
            self._logger.warning(f"Document {doc.id} created but summarization failed: {e}")

    async def _chunk_document(
        self, session, doc, content: str, auto_chunk: bool, max_tokens: int, total_tokens: int
    ) -> tuple[int, int]:
        """Auto-chunk a vision document if enabled.

        Args:
            session: Database session
            doc: VisionDocument ORM instance
            content: Document text content
            auto_chunk: Whether auto-chunking is enabled
            max_tokens: Max tokens per chunk
            total_tokens: Current token estimate

        Returns:
            Tuple of (chunks_created, total_tokens)
        """
        chunks_created = 0

        if not auto_chunk:
            return chunks_created, total_tokens

        from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

        chunker = VisionDocumentChunker(target_chunk_size=max_tokens)

        try:
            chunk_result = await chunker.chunk_vision_document(
                session=session, tenant_key=self.tenant_key, vision_document_id=str(doc.id)
            )

            await session.commit()

            chunks_created = chunk_result["chunks_created"]
            total_tokens = chunk_result["total_tokens"]

            self._logger.info(f"Chunked document {doc.id}: {chunks_created} chunks, {total_tokens} tokens")
        except (ContextError, GiljoFileNotFoundError, OSError) as e:
            self._logger.warning(f"Document {doc.id} created but chunking failed: {e}")

        return chunks_created, total_tokens

    async def _consolidate_vision(self, session, product_id: str) -> None:
        """Auto-consolidate vision documents after upload.

        Handover 0493: Ensures light/medium summaries are always available.

        Args:
            session: Database session
            product_id: Product UUID
        """
        try:
            from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

            consolidation_service = ConsolidatedVisionService()
            await consolidation_service.consolidate_vision_documents(
                product_id=product_id,
                session=session,
                tenant_key=self.tenant_key,
                force=True,
            )
            self._logger.info(f"Auto-consolidated vision documents for product {product_id}")
        except (ValidationError, ResourceNotFoundError, ValueError, KeyError) as e:
            self._logger.warning(f"Auto-consolidation failed for product {product_id}: {e}")

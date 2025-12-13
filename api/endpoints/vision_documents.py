"""
Vision Documents API Endpoints for Handover 0043 Phase 5.

Implements REST API for multi-vision document support:
- POST / - Create vision document with file upload or inline content
- GET /product/{product_id} - List all vision documents for a product
- PUT /{document_id} - Update vision document content with auto re-chunk
- DELETE /{document_id} - Delete vision document with CASCADE chunks
- POST /{document_id}/rechunk - Trigger re-chunking

All endpoints enforce multi-tenant isolation via get_tenant_key() dependency.
File uploads use cross-platform path handling with pathlib.Path.
"""

import logging
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_key
from api.schemas.vision_document import (
    DeleteResponse,
    RechunkResponse,
    VisionDocumentResponse,
)
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Vision Documents"])


async def get_db():
    """
    Get database session dependency (async).

    Returns:
        AsyncSession: SQLAlchemy async database session
    """
    from api.app import state

    if not state.db_manager:
        raise RuntimeError("Database manager not initialized")

    # Get an async session context manager
    async with state.db_manager.get_session_async() as session:
        yield session


def get_vision_repo():
    """
    Get VisionDocumentRepository instance.

    Returns:
        VisionDocumentRepository: Repository instance
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not available")

    return VisionDocumentRepository(state.db_manager)


@router.post("/", response_model=VisionDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_vision_document(
    product_id: str = Form(...),
    document_name: str = Form(...),
    document_type: str = Form("vision"),
    content: Optional[str] = Form(None),
    vision_file: Optional[UploadFile] = File(None),
    auto_chunk: bool = Form(True),
    display_order: int = Form(0),
    version: str = Form("1.0.0"),
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Create a new vision document for a product.

    **Storage Options**:
    - **File Upload**: Provide `vision_file` (sets storage_type="file")
    - **Inline Content**: Provide `content` (sets storage_type="inline")
    - **Both**: Provide both (sets storage_type="hybrid")

    **Auto-Chunking**:
    - If `auto_chunk=True` (default), document is chunked immediately using EnhancedChunker
    - Chunks are stored in MCPContextIndex with vision_document_id link

    **Cross-Platform Path Handling**:
    - Uses pathlib.Path for all file operations (Windows/Linux/Mac compatible)
    - Storage path: `./products/{product_id}/vision/{filename}`

    Args:
        product_id: Product ID this document belongs to
        document_name: User-friendly document name
        document_type: Document category (vision, architecture, features, etc.)
        content: Inline document content (optional)
        vision_file: Uploaded file (optional)
        auto_chunk: Automatically chunk document after creation (default: True)
        display_order: Display order in UI (default: 0)
        version: Semantic version (default: "1.0.0")

    Returns:
        VisionDocumentResponse: Created vision document

    Raises:
        HTTPException 400: If neither content nor file provided
        HTTPException 404: If product not found
        HTTPException 500: If creation or chunking fails
    """
    try:
        # DEBUG: Log tenant_key and product_id
        logger.info(f"[VisionDoc Upload] product_id={product_id}, tenant_key={tenant_key}")

        # Validate product exists and belongs to tenant (ASYNC query)
        result = await db.execute(select(Product).filter(Product.id == product_id, Product.tenant_key == tenant_key))
        product = result.scalar_one_or_none()

        # DEBUG: Log query result
        logger.info(f"[VisionDoc Upload] Product found: {bool(product)}")
        if not product:
            # DEBUG: Check if product exists with different tenant_key
            all_result = await db.execute(select(Product).filter(Product.id == product_id))
            any_product = all_result.scalar_one_or_none()
            if any_product:
                logger.warning(
                    f"[VisionDoc Upload] Product exists but tenant mismatch! Product tenant: {any_product.tenant_key}, Request tenant: {tenant_key}"
                )

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")

        # Determine storage type and get content
        document_content = content
        storage_type = "inline"
        file_path = None
        file_size = None

        if vision_file:
            # File uploaded - save using cross-platform Path handling
            storage_path = Path("./products") / product_id / "vision"
            storage_path.mkdir(parents=True, exist_ok=True)  # CROSS-PLATFORM: creates subdirs

            file_path = storage_path / vision_file.filename
            async with aiofiles.open(file_path, "wb") as f:
                content_bytes = await vision_file.read()
                await f.write(content_bytes)

            # Calculate file size from uploaded file
            file_size = len(content_bytes)

            document_content = content_bytes.decode("utf-8")
            storage_type = "hybrid" if content else "file"
        elif content:
            # Inline content - calculate size from string
            file_size = len(content.encode("utf-8"))

        if not document_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content provided. Provide either 'content' or 'vision_file'.",
            )

        # Create vision document
        # IMPORTANT: Store path with forward slashes (OS-neutral, prevents escape sequence bugs)
        normalized_path = str(file_path).replace("\\", "/") if file_path else None

        doc = await vision_repo.create(
            session=db,
            tenant_key=tenant_key,
            product_id=product_id,
            document_name=document_name,
            content=document_content,
            document_type=document_type,
            storage_type=storage_type,
            file_path=normalized_path,
            file_size=file_size,
            display_order=display_order,
            version=version,
        )
        await db.commit()

        # Optionally chunk immediately
        if auto_chunk:
            try:
                from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

                chunker = VisionDocumentChunker()
                result = await chunker.chunk_vision_document(db, tenant_key, doc.id)

                if not result.get("success"):
                    # Chunking failed - rollback document creation (fail-fast)
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Document upload failed during chunking: {result.get('error')}",
                    )

            except HTTPException:
                raise
            except Exception as chunk_error:
                logger.error(f"Chunking error for document {doc.id}: {chunk_error}", exc_info=True)
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Document upload failed during chunking: {chunk_error!s}",
                )

        # Generate multi-level summaries (Sumy LSA compression)
        # Threshold: 5K tokens (smallest summary level)
        total_tokens = len(document_content) // 4  # Rough estimate: 1 token ≈ 4 chars
        if total_tokens > 5000:
            try:
                from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

                logger.info(f"Generating multi-level summaries for doc {doc.id}: {total_tokens} tokens")

                summarizer = VisionDocumentSummarizer()
                summaries = summarizer.summarize_multi_level(document_content)

                # Re-attach doc to session and store summaries
                db.add(doc)
                doc.summary_light = summaries["light"]["summary"]
                doc.summary_moderate = summaries["moderate"]["summary"]
                doc.summary_heavy = summaries["heavy"]["summary"]
                doc.summary_light_tokens = summaries["light"]["tokens"]
                doc.summary_moderate_tokens = summaries["moderate"]["tokens"]
                doc.summary_heavy_tokens = summaries["heavy"]["tokens"]
                doc.is_summarized = True
                doc.original_token_count = summaries["original_tokens"]

                await db.commit()

                logger.info(
                    f"Vision document {doc.id} summarized: "
                    f"Low={summaries['light']['tokens']} tokens, "
                    f"Medium={summaries['moderate']['tokens']} tokens, "
                    f"High={summaries['heavy']['tokens']} tokens "
                    f"(from {summaries['original_tokens']} tokens) "
                    f"in {summaries['processing_time_ms']}ms"
                )
            except Exception as e:
                # Summarization failed but document created - log warning and continue
                logger.warning(f"Document {doc.id} created but summarization failed: {e}")

        await db.refresh(doc)

        return VisionDocumentResponse.model_validate(doc)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create vision document: {e!s}"
        )


@router.get("/product/{product_id}", response_model=List[VisionDocumentResponse])
async def list_vision_documents(
    product_id: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    List all vision documents for a product.

    **Multi-Tenant Isolation**: Only returns documents for the authenticated tenant.

    **Filtering**:
    - `active_only=True` (default): Returns only active documents
    - `active_only=False`: Returns all documents including inactive/archived

    **Ordering**: Results ordered by display_order ASC, created_at ASC

    Args:
        product_id: Product ID to list documents for
        active_only: If True, only return active documents (default: True)

    Returns:
        List[VisionDocumentResponse]: List of vision documents

    Raises:
        HTTPException 500: If listing fails
    """
    try:
        docs = await vision_repo.list_by_product(
            session=db, tenant_key=tenant_key, product_id=product_id, active_only=active_only
        )

        return [VisionDocumentResponse.model_validate(doc) for doc in docs]

    except Exception as e:
        logger.error(f"Failed to list vision documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list vision documents: {e!s}"
        )


@router.put("/{document_id}", response_model=VisionDocumentResponse)
async def update_vision_document(
    document_id: str,
    content: str = Form(...),
    auto_rechunk: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Update vision document content.

    **Automatic Updates**:
    - Recalculates content hash (SHA-256)
    - Resets chunked flag to False (content changed)
    - Resets chunk_count to 0
    - Updates updated_at timestamp

    **Auto Re-Chunking**:
    - If `auto_rechunk=True` (default), document is re-chunked immediately
    - Old chunks are deleted first (by vision_document_id)
    - New chunks are created from updated content

    Args:
        document_id: Document ID to update
        content: New document content
        auto_rechunk: Automatically re-chunk after update (default: True)

    Returns:
        VisionDocumentResponse: Updated vision document

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If update or re-chunking fails
    """
    try:
        # Update content
        doc = await vision_repo.update_content(
            session=db, tenant_key=tenant_key, document_id=document_id, new_content=content
        )

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Vision document {document_id} not found"
            )

        await db.commit()

        # Optionally re-chunk
        if auto_rechunk:
            try:
                from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

                chunker = VisionDocumentChunker()
                result = await chunker.chunk_vision_document(db, tenant_key, document_id)

                if not result.get("success"):
                    logger.warning(f"Re-chunking failed for document {document_id}: {result.get('error')}")
                    # Don't rollback - content update succeeded, chunking can be retried

            except Exception as chunk_error:
                logger.error(f"Re-chunking error for document {document_id}: {chunk_error}", exc_info=True)
                # Continue - content updated successfully, chunking can be retried later

        await db.refresh(doc)

        return VisionDocumentResponse.model_validate(doc)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update vision document: {e!s}"
        )


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_vision_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Delete vision document and all associated chunks.

    **CASCADE Deletion**:
    - Deletes VisionDocument record
    - Automatically deletes all MCPContextIndex chunks (via vision_document_id CASCADE)

    **Multi-Tenant Isolation**: Only allows deletion of documents belonging to tenant.

    Args:
        document_id: Document ID to delete

    Returns:
        DeleteResponse: Deletion result with chunks_deleted count

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If deletion fails
    """
    try:
        result = await vision_repo.delete(session=db, tenant_key=tenant_key, document_id=document_id)

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])

        await db.commit()

        return DeleteResponse(**result)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete vision document: {e!s}"
        )


@router.post("/{document_id}/rechunk", response_model=RechunkResponse)
async def rechunk_vision_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Trigger re-chunking of a vision document.

    **Re-Chunking Process**:
    1. Get vision document content
    2. Delete existing chunks (by vision_document_id)
    3. Chunk content using EnhancedChunker
    4. Create new chunks in MCPContextIndex
    5. Update vision document metadata (chunked=True, chunk_count, total_tokens)

    **Use Cases**:
    - Content was updated without auto_rechunk
    - Chunking failed during creation/update
    - Chunker algorithm changed (want to re-chunk with new logic)

    Args:
        document_id: Document ID to re-chunk

    Returns:
        RechunkResponse: Re-chunking result with chunks_created count

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If re-chunking fails
    """
    try:
        from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

        # Verify document exists and belongs to tenant
        doc = await vision_repo.get_by_id(db, tenant_key, document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Vision document {document_id} not found"
            )

        # Trigger re-chunking
        chunker = VisionDocumentChunker()
        result = await chunker.chunk_vision_document(db, tenant_key, document_id)

        if not result.get("success"):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Chunking failed: {result.get('error')}"
            )

        await db.commit()

        return RechunkResponse(**result)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to rechunk vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rechunk vision document: {e!s}"
        )

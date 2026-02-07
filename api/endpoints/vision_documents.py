"""
Vision Documents API Endpoints.

Implements REST API for vision document management:
- POST / - Create vision document with file upload or inline content
- GET /product/{product_id} - List all vision documents for a product
- PUT /{document_id} - Update vision document content
- DELETE /{document_id} - Delete vision document

All endpoints enforce multi-tenant isolation via get_tenant_key() dependency.
File uploads use cross-platform path handling with pathlib.Path.

Handover 0246b: Simplified storage - complete documents stored in vision_document TEXT column.
Summaries (light/medium) generated via VisionDocumentSummarizer for large documents.
"""

import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_key
from api.schemas.vision_document import (
    DeleteResponse,
    RechunkResponse,
    VisionDocumentResponse,
)
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Vision Documents"])


async def trigger_consolidation(product_id: str, tenant_key: str, db_session: AsyncSession) -> None:
    """
    Queue consolidation job for product after vision document changes.

    Runs synchronously since consolidation is relatively fast (~1-2 seconds).
    Does not block main operation - logs warning if consolidation fails but
    still returns success for the vision document operation.

    Handover 0377 Phase 4: Automatic consolidation trigger.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        db_session: Database session (reuses endpoint's session)
    """
    try:
        consolidation_service = ConsolidatedVisionService()
        result = await consolidation_service.consolidate_vision_documents(
            product_id=product_id, session=db_session, tenant_key=tenant_key, force=False
        )

        if result["success"]:
            logger.info(
                f"vision_documents_consolidated: product_id={product_id}, "
                f"light_tokens={result['light']['tokens']}, medium_tokens={result['medium']['tokens']}"
            )
        else:
            # Not an error - could be "no_changes" which is expected
            logger.debug(f"consolidation_skipped: product_id={product_id}, reason={result.get('error')}")
    except (SQLAlchemyError, ValueError, KeyError):
        # Don't fail the main operation if consolidation fails
        logger.exception(f"consolidation_failed: product_id={product_id}")


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
    content: str | None = Form(None),
    vision_file: UploadFile | None = File(None),
    display_order: int = Form(0),
    version: str = Form("1.0.0"),
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Create a new vision document for a product.

    **Storage**: Complete document stored in `vision_document` TEXT column.

    **Summarization**: Large documents (>5K tokens) automatically generate:
    - Light summary (33% of original)
    - Medium summary (66% of original)

    **Storage Options**:
    - **File Upload**: Provide `vision_file` (sets storage_type="file")
    - **Inline Content**: Provide `content` (sets storage_type="inline")
    - **Both**: Provide both (sets storage_type="hybrid")

    **Cross-Platform Path Handling**:
    - Uses pathlib.Path for all file operations (Windows/Linux/Mac compatible)
    - Storage path: `./products/{product_id}/vision/{filename}`

    Args:
        product_id: Product ID this document belongs to
        document_name: User-friendly document name
        document_type: Document category (vision, architecture, features, etc.)
        content: Inline document content (optional)
        vision_file: Uploaded file (optional)
        display_order: Display order in UI (default: 0)
        version: Semantic version (default: "1.0.0")

    Returns:
        VisionDocumentResponse: Created vision document

    Raises:
        HTTPException 400: If neither content nor file provided
        HTTPException 404: If product not found
        HTTPException 500: If creation or summarization fails
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

            # Try UTF-8 first, fallback to latin-1 for Windows files with special chars (e.g., degree symbol)
            try:
                document_content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(f"File {vision_file.filename} is not UTF-8 encoded, falling back to latin-1")
                document_content = content_bytes.decode("latin-1")
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

        # Generate multi-level summaries (Sumy LSA compression)
        # Handover 0377: Summarize all documents (100 token minimum to skip empty/trivial files)
        # Light=33%, Medium=66%, Full=100% (original)
        total_tokens = len(document_content) // 4  # Rough estimate: 1 token ≈ 4 chars
        if total_tokens > 100:  # Summarize all non-trivial documents
            try:
                from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

                logger.info(f"Generating multi-level summaries for doc {doc.id}: {total_tokens} tokens")

                summarizer = VisionDocumentSummarizer()
                summaries = summarizer.summarize_multi_level(document_content)

                # Re-attach doc to session and store summaries (Handover 0246b: light and medium only)
                db.add(doc)
                doc.summary_light = summaries["light"]["summary"]
                doc.summary_medium = summaries["medium"]["summary"]
                doc.summary_light_tokens = summaries["light"]["tokens"]
                doc.summary_medium_tokens = summaries["medium"]["tokens"]
                doc.is_summarized = True
                doc.original_token_count = summaries["original_tokens"]

                await db.commit()

                logger.info(
                    f"Vision document {doc.id} summarized: "
                    f"Light={summaries['light']['tokens']} tokens, "
                    f"Medium={summaries['medium']['tokens']} tokens "
                    f"(from {summaries['original_tokens']} tokens) "
                    f"in {summaries['processing_time_ms']}ms"
                )
            except (ImportError, ValueError, KeyError) as e:
                # Summarization failed but document created - log warning and continue
                logger.warning(f"Document {doc.id} created but summarization failed: {e}")

        # Auto-chunk large documents (>25K tokens) for pagination support
        # Handover 0347: Restore chunking removed in 0246b (Claude Code 25K limit)
        if total_tokens > 25000:
            try:
                from src.giljo_mcp.context_management.chunker import VisionDocumentChunker

                logger.info(f"Chunking document {doc.id}: {total_tokens} tokens exceeds 25K threshold")

                chunker = VisionDocumentChunker(target_chunk_size=25000)
                chunk_result = await chunker.chunk_vision_document(
                    session=db, tenant_key=tenant_key, vision_document_id=str(doc.id)
                )
                await db.commit()

                if chunk_result.get("success"):
                    logger.info(
                        f"Chunked document {doc.id}: {chunk_result.get('chunks_created', 0)} chunks, "
                        f"{chunk_result.get('total_tokens', 0)} tokens"
                    )
                else:
                    logger.warning(f"Document {doc.id} created but chunking failed: {chunk_result.get('error')}")
            except (ImportError, SQLAlchemyError, ValueError) as e:
                # Chunking failed but document created - log warning and continue
                logger.warning(f"Document {doc.id} created but chunking failed: {e}")

        # Handover 0377 Phase 4: Trigger consolidation after document upload
        await trigger_consolidation(product_id, tenant_key, db)

        await db.refresh(doc)

        return VisionDocumentResponse.model_validate(doc)

    except HTTPException:
        await db.rollback()
        raise
    except (SQLAlchemyError, OSError, UnicodeDecodeError, ValueError) as e:
        await db.rollback()
        logger.error(f"Failed to create vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create vision document: {e!s}"
        ) from e


@router.get("/{document_id}", response_model=VisionDocumentResponse)
async def get_vision_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Get a single vision document by ID.

    **Handover 0246b**: Returns full document including vision_document content.
    Used for "Full" preview in product details dialog.

    **Multi-Tenant Isolation**: Only returns document if it belongs to the authenticated tenant.

    Args:
        document_id: Vision document ID

    Returns:
        VisionDocumentResponse with full content

    Raises:
        404: Document not found or belongs to different tenant
    """
    from src.giljo_mcp.models import VisionDocument

    result = await db.execute(
        select(VisionDocument).where(
            VisionDocument.id == document_id,
            VisionDocument.tenant_key == tenant_key,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vision document {document_id} not found")

    return VisionDocumentResponse.model_validate(doc)


@router.get("/product/{product_id}", response_model=list[VisionDocumentResponse])
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

    except SQLAlchemyError as e:
        logger.error(f"Failed to list vision documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list vision documents: {e!s}"
        ) from e


@router.put("/{document_id}", response_model=VisionDocumentResponse)
async def update_vision_document(
    document_id: str,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Update vision document content.

    **Automatic Updates**:
    - Recalculates content hash (SHA-256)
    - Updates updated_at timestamp
    - Regenerates summaries for large documents (>5K tokens)

    Args:
        document_id: Document ID to update
        content: New document content

    Returns:
        VisionDocumentResponse: Updated vision document

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If update or summarization fails
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

        # Regenerate summaries for large documents
        # Handover 0377: Summarize all documents (100 token minimum to skip empty/trivial files)
        # Light=33%, Medium=66%, Full=100% (original)
        total_tokens = len(content) // 4  # Rough estimate: 1 token ≈ 4 chars
        if total_tokens > 100:  # Summarize all non-trivial documents
            try:
                from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

                logger.info(f"Regenerating summaries for updated doc {document_id}: {total_tokens} tokens")

                summarizer = VisionDocumentSummarizer()
                summaries = summarizer.summarize_multi_level(content)

                # Update summaries (Handover 0246b: light and medium only)
                db.add(doc)
                doc.summary_light = summaries["light"]["summary"]
                doc.summary_medium = summaries["medium"]["summary"]
                doc.summary_light_tokens = summaries["light"]["tokens"]
                doc.summary_medium_tokens = summaries["medium"]["tokens"]
                doc.is_summarized = True
                doc.original_token_count = summaries["original_tokens"]

                await db.commit()

                logger.info(
                    f"Vision document {document_id} summaries updated: "
                    f"Light={summaries['light']['tokens']} tokens, "
                    f"Medium={summaries['medium']['tokens']} tokens"
                )
            except (ImportError, ValueError, KeyError) as e:
                # Summarization failed but content updated - log warning and continue
                logger.warning(f"Document {document_id} updated but summarization failed: {e}")

        # Handover 0377 Phase 4: Trigger consolidation after document update
        # Get product_id from the updated document
        await trigger_consolidation(doc.product_id, tenant_key, db)

        await db.refresh(doc)

        return VisionDocumentResponse.model_validate(doc)

    except HTTPException:
        await db.rollback()
        raise
    except (SQLAlchemyError, ValueError) as e:
        await db.rollback()
        logger.error(f"Failed to update vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update vision document: {e!s}"
        ) from e


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
        # Get document before deletion to retrieve product_id for consolidation
        from src.giljo_mcp.models import VisionDocument

        result = await db.execute(
            select(VisionDocument).where(
                VisionDocument.id == document_id,
                VisionDocument.tenant_key == tenant_key,
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Vision document {document_id} not found"
            )

        product_id = doc.product_id  # Store before deletion

        # Delete the document
        delete_result = await vision_repo.delete(session=db, tenant_key=tenant_key, document_id=document_id)

        if not delete_result["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=delete_result["message"])

        await db.commit()

        # Handover 0377 Phase 4: Trigger consolidation after document deletion
        await trigger_consolidation(product_id, tenant_key, db)

        return DeleteResponse(**delete_result)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Failed to delete vision document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete vision document: {e!s}"
        ) from e


@router.post("/products/{product_id}/regenerate-consolidated", response_model=dict)
async def regenerate_consolidated_vision(
    product_id: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Manually regenerate consolidated vision summaries for a product.

    **Handover 0377 Phase 4**: Admin endpoint for forcing regeneration.

    **Use Cases**:
    - Consolidation algorithm changed (want to regenerate with new logic)
    - Manual refresh after bulk vision document updates
    - Testing/debugging consolidation behavior

    **Force Parameter**:
    - `force=False` (default): Only regenerate if content hash changed
    - `force=True`: Always regenerate even if content unchanged

    Args:
        product_id: Product ID to regenerate consolidated vision for
        force: Force regeneration even if no changes detected

    Returns:
        {
            "success": bool,
            "light_tokens": int,
            "medium_tokens": int,
            "source_docs": ["doc_id1", ...],
            "hash": "sha256_hash"
        }

    Raises:
        HTTPException 400: If consolidation fails or skipped
        HTTPException 404: If product not found
    """
    try:
        # Verify product exists and belongs to tenant
        result = await db.execute(select(Product).filter(Product.id == product_id, Product.tenant_key == tenant_key))
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")

        # Run consolidation service
        consolidation_service = ConsolidatedVisionService()
        consolidation_result = await consolidation_service.consolidate_vision_documents(
            product_id=product_id, session=db, tenant_key=tenant_key, force=force
        )

        if not consolidation_result["success"]:
            # Return error details for debugging
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=consolidation_result.get("error", "Consolidation failed"),
            )

        return {
            "success": True,
            "light_tokens": consolidation_result["light"]["tokens"],
            "medium_tokens": consolidation_result["medium"]["tokens"],
            "source_docs": consolidation_result["source_docs"],
            "hash": consolidation_result["hash"],
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except (SQLAlchemyError, ValueError, KeyError) as e:
        logger.error(f"Failed to regenerate consolidated vision: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to regenerate consolidated vision: {e!s}"
        ) from e


@router.post("/{document_id}/regenerate-summaries", response_model=RechunkResponse)
async def regenerate_summaries(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key),
    vision_repo: VisionDocumentRepository = Depends(get_vision_repo),
):
    """
    Regenerate summaries for a vision document.

    **Regeneration Process**:
    1. Get vision document content
    2. Generate light and medium summaries using LSA
    3. Update document with new summaries

    **Use Cases**:
    - Summarization failed during creation/update
    - Want to regenerate summaries after algorithm changes

    Args:
        document_id: Document ID to regenerate summaries for

    Returns:
        RechunkResponse: Result with success status (reusing schema for compatibility)

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If summarization fails
    """
    try:
        from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

        # Verify document exists and belongs to tenant
        doc = await vision_repo.get_by_id(db, tenant_key, document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Vision document {document_id} not found"
            )

        # Get document content
        content = doc.vision_document
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vision document {document_id} has no content to summarize",
            )

        # Generate summaries
        logger.info(f"Regenerating summaries for doc {document_id}")
        summarizer = VisionDocumentSummarizer()
        summaries = summarizer.summarize_multi_level(content)

        # Update document
        db.add(doc)
        doc.summary_light = summaries["light"]["summary"]
        doc.summary_medium = summaries["medium"]["summary"]
        doc.summary_light_tokens = summaries["light"]["tokens"]
        doc.summary_medium_tokens = summaries["medium"]["tokens"]
        doc.is_summarized = True
        doc.original_token_count = summaries["original_tokens"]

        await db.commit()

        logger.info(
            f"Vision document {document_id} summaries regenerated: "
            f"Light={summaries['light']['tokens']} tokens, "
            f"Medium={summaries['medium']['tokens']} tokens"
        )

        return RechunkResponse(
            success=True,
            message="Summaries regenerated successfully",
            chunks_created=2,  # light and medium summaries
            total_tokens=summaries["original_tokens"],
        )

    except HTTPException:
        await db.rollback()
        raise
    except (ImportError, SQLAlchemyError, ValueError, KeyError) as e:
        await db.rollback()
        logger.error(f"Failed to regenerate summaries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to regenerate summaries: {e!s}"
        ) from e

# ruff: noqa: B904, N806, UP006, PERF401
"""
Product Vision Document Endpoints - Handover 0503

Handles vision document upload and retrieval operations using ProductService.

Handover 0503: Consolidated vision endpoints, updated paths, added proper response schemas.
Handover 0126: Initial implementation with direct database access.
"""

import logging
from typing import List  # noqa: UP035

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_key
from api.endpoints.dependencies import get_product_service
from api.schemas.vision_document import VisionDocumentResponse
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import User
from src.giljo_mcp.services.product_service import ProductService

from .models import VisionChunk


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{product_id}/vision", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_vision_document(
    product_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
    product_service: ProductService = Depends(get_product_service),
) -> dict:
    """
    Upload vision document for product with automatic chunking.

    Accepts markdown/text files up to 10MB. Documents are automatically
    chunked at 25K tokens using semantic boundaries (headers, paragraphs).

    Handover 0503: Updated path from /upload-vision to /vision (canonical endpoint).
    Handover 0500: Implemented vision upload with intelligent chunking.
    """
    logger.info(f"User {current_user.username} uploading vision document '{file.filename}' for product {product_id}")

    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Validate file type (markdown/text)
    allowed_extensions = [".md", ".txt", ".markdown"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Upload via ProductService (uses injected dependency)
        result = await product_service.upload_vision_document(
            product_id=product_id,
            content=content_str,
            filename=file.filename,
            auto_chunk=True,
            max_tokens=25000,
        )

        logger.info(
            f"Successfully uploaded vision document {result['document_id']}: "
            f"{result['chunks_created']} chunks, {result['total_tokens']} tokens"
        )

        return {
            "success": True,
            "message": "Vision document uploaded and chunked successfully",
            "document_id": result["document_id"],
            "document_name": result["document_name"],
            "chunks_created": result["chunks_created"],
            "total_tokens": result["total_tokens"],
        }

    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be valid UTF-8 encoded text")
    except ValueError as e:
        # Handover 0508: Catch validation errors from ProductService
        error_msg = str(e).lower()
        if "already exists" in error_msg or "duplicate" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A vision document named '{file.filename}' already exists for this product. Please rename your file and try again.",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Vision upload failed")
        # Handover 0508: Check for IntegrityError (duplicate constraint violation)
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str or "uq_vision_doc" in error_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A vision document named '{file.filename}' already exists for this product. Please rename your file and try again.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again or contact support.",
        )


@router.get("/{product_id}/vision", response_model=List[VisionDocumentResponse])
async def list_vision_documents(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> List[VisionDocumentResponse]:
    """
    List all vision documents for a product.

    Returns complete vision document records with metadata.

    Handover 0503: Added GET endpoint for listing vision documents.
    """
    from sqlalchemy import and_, select

    from src.giljo_mcp.models import VisionDocument

    logger.debug(f"User {current_user.username} listing vision documents for product {product_id}")

    try:
        # Query vision documents for this product
        stmt = (
            select(VisionDocument)
            .where(
                and_(
                    VisionDocument.tenant_key == tenant_key,
                    VisionDocument.product_id == product_id,
                )
            )
            .order_by(VisionDocument.display_order, VisionDocument.created_at)
        )

        result = await db.execute(stmt)
        documents = result.scalars().all()

        # Convert to response models
        response_docs = []
        for doc in documents:
            # Check if summaries exist
            has_summaries = bool(doc.summary_light or doc.summary_medium)

            response_docs.append(
                VisionDocumentResponse(
                    id=doc.id,
                    tenant_key=doc.tenant_key,
                    product_id=doc.product_id,
                    document_name=doc.document_name,
                    document_type=doc.document_type,
                    storage_type=doc.storage_type,
                    vision_path=doc.vision_path,
                    vision_document=doc.vision_document,
                    chunked=doc.chunked,
                    chunk_count=doc.chunk_count,
                    total_tokens=doc.total_tokens,
                    file_size=doc.file_size,
                    content_hash=doc.content_hash,
                    version=doc.version,
                    is_active=doc.is_active,
                    display_order=doc.display_order,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                    chunked_at=None,  # VisionDocument model does not have chunked_at field
                    meta_data=doc.meta_data or {},
                    # Summary fields (Handover 0246b: light/medium only)
                    summary_light=doc.summary_light,
                    summary_medium=doc.summary_medium,
                    summary_light_tokens=doc.summary_light_tokens,
                    summary_medium_tokens=doc.summary_medium_tokens,
                    has_summaries=has_summaries,
                )
            )

        logger.debug(f"Retrieved {len(response_docs)} vision documents for product {product_id}")

        return response_docs

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list vision documents")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{product_id}/vision/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vision_document(
    product_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Delete a vision document by ID.

    Removes the vision document and its associated chunks (CASCADE).

    Handover 0503: Added DELETE endpoint for vision documents.
    """
    from sqlalchemy import and_, delete, select

    from src.giljo_mcp.models import MCPContextIndex, VisionDocument

    logger.info(f"User {current_user.username} deleting vision document {doc_id} for product {product_id}")

    try:
        # Verify document exists and belongs to this product/tenant
        stmt = select(VisionDocument).where(
            and_(
                VisionDocument.id == doc_id,
                VisionDocument.product_id == product_id,
                VisionDocument.tenant_key == tenant_key,
            )
        )

        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vision document not found")

        # Delete associated chunks first
        delete_chunks_stmt = delete(MCPContextIndex).where(
            and_(
                MCPContextIndex.vision_document_id == doc_id,
                MCPContextIndex.tenant_key == tenant_key,
            )
        )
        await db.execute(delete_chunks_stmt)

        # Delete the vision document
        await db.delete(doc)
        await db.commit()

        logger.info(f"Successfully deleted vision document {doc_id}")

        return

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete vision document")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{product_id}/vision-chunks", response_model=List[VisionChunk])
async def get_vision_chunks(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> List[VisionChunk]:
    """
    Get vision document chunks for product (legacy endpoint).

    Returns all context chunks associated with product's vision documents.
    Chunks are ordered by vision_document_id and chunk_order.

    Note: Consider using GET /{product_id}/vision instead for full document metadata.

    Handover 0500: Implemented vision chunks retrieval.
    """
    from sqlalchemy import and_, select

    from src.giljo_mcp.models import MCPContextIndex

    logger.debug(f"User {current_user.username} retrieving vision chunks for product {product_id}")

    try:
        # Query context chunks for this product
        stmt = (
            select(MCPContextIndex)
            .where(
                and_(
                    MCPContextIndex.tenant_key == tenant_key,
                    MCPContextIndex.product_id == product_id,
                    MCPContextIndex.vision_document_id.isnot(None),
                )
            )
            .order_by(MCPContextIndex.vision_document_id, MCPContextIndex.chunk_order)
        )

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        # Convert to response model
        response_chunks = []
        for chunk in chunks:
            response_chunks.append(
                VisionChunk(
                    chunk_number=chunk.chunk_order,
                    total_chunks=len(chunks),
                    content=chunk.content,
                    char_start=0,  # Not tracked in current schema
                    char_end=len(chunk.content),
                    boundary_type="semantic",  # Default boundary type
                    keywords=chunk.keywords or [],
                    headers=chunk.summary.split("\n") if chunk.summary else [],
                )
            )

        logger.debug(f"Retrieved {len(response_chunks)} vision chunks for product {product_id}")

        return response_chunks

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to retrieve vision chunks")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

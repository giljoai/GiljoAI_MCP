"""
Product Vision Document Endpoints - Handover 0126

Handles vision document upload and retrieval operations.

NOTE: ProductService does not exist yet. This implementation uses direct
database access temporarily. Future work: Create ProductService and refactor.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from .models import VisionChunk


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{product_id}/upload-vision", response_model=dict)
async def upload_vision_document(
    product_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> dict:
    """
    Upload vision document for product with automatic chunking.
    
    Accepts markdown/text files up to 10MB. Documents are automatically
    chunked at 25K tokens using semantic boundaries (headers, paragraphs).
    
    Handover 0500: Implemented vision upload with intelligent chunking.
    """
    from src.giljo_mcp.services.product_service import ProductService
    from src.giljo_mcp.db_manager import DatabaseManager
    
    logger.info(
        f"User {current_user.username} uploading vision document "
        f"'{file.filename}' for product {product_id}"
    )
    
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Validate file type (markdown/text)
    allowed_extensions = [".md", ".txt", ".markdown"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Upload via ProductService
        db_manager = DatabaseManager()
        product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)
        
        result = await product_service.upload_vision_document(
            product_id=product_id,
            content=content_str,
            filename=file.filename,
            auto_chunk=True,
            max_tokens=25000,
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Vision upload failed")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid UTF-8 encoded text"
        )
    except Exception as e:
        logger.exception(f"Vision upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision upload failed: {str(e)}"
        )


@router.get("/{product_id}/vision-chunks", response_model=List[VisionChunk])
async def get_vision_chunks(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    tenant_key: str = Depends(get_tenant_key),
) -> List[VisionChunk]:
    """
    Get vision document chunks for product.
    
    Returns all context chunks associated with product's vision documents.
    Chunks are ordered by vision_document_id and chunk_order.
    
    Handover 0500: Implemented vision chunks retrieval.
    """
    from src.giljo_mcp.repositories.context_repository import ContextRepository
    from src.giljo_mcp.db_manager import DatabaseManager
    from sqlalchemy import select, and_
    from src.giljo_mcp.models import MCPContextIndex
    
    logger.debug(
        f"User {current_user.username} retrieving vision chunks "
        f"for product {product_id}"
    )
    
    try:
        # Query context chunks for this product
        stmt = select(MCPContextIndex).where(
            and_(
                MCPContextIndex.tenant_key == tenant_key,
                MCPContextIndex.product_id == product_id,
                MCPContextIndex.vision_document_id.isnot(None)
            )
        ).order_by(
            MCPContextIndex.vision_document_id,
            MCPContextIndex.chunk_order
        )
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        # Convert to response model
        response_chunks = []
        for idx, chunk in enumerate(chunks):
            response_chunks.append(VisionChunk(
                chunk_number=chunk.chunk_order,
                total_chunks=len(chunks),
                content=chunk.content,
                char_start=0,  # Not tracked in current schema
                char_end=len(chunk.content),
                boundary_type="semantic",  # Default boundary type
                keywords=chunk.keywords or [],
                headers=chunk.summary.split("\n") if chunk.summary else [],
            ))
        
        logger.debug(f"Retrieved {len(response_chunks)} vision chunks for product {product_id}")
        
        return response_chunks
        
    except Exception as e:
        logger.exception(f"Failed to retrieve vision chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve vision chunks: {str(e)}"
        )

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
    Upload vision document for product.

    TODO: Refactor to use ProductService.upload_vision() once service exists.
    """
    logger.info(f"User {current_user.username} uploading vision document for product {product_id}")

    # TODO: Implement vision document upload logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ProductService.upload_vision not yet implemented"
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

    TODO: Refactor to use ProductService.get_vision_chunks() once service exists.
    """
    logger.debug(f"User {current_user.username} retrieving vision chunks for product {product_id}")

    # TODO: Implement vision chunks retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ProductService.get_vision_chunks not yet implemented"
    )

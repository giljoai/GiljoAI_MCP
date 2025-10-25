"""
Vision Document API Pydantic schemas for Handover 0043 Phase 5.

Provides request/response models for:
- Vision document creation (POST /vision-documents/)
- Vision document listing (GET /vision-documents/product/{product_id})
- Vision document updates (PUT /vision-documents/{document_id})
- Vision document deletion (DELETE /vision-documents/{document_id})
- Re-chunking (POST /vision-documents/{document_id}/rechunk)
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class VisionDocumentCreate(BaseModel):
    """
    Schema for creating a vision document.

    Users can choose between:
    - File upload (vision_file) → storage_type="file"
    - Inline content (content) → storage_type="inline"
    - Both (hybrid) → storage_type="hybrid"
    """
    product_id: str = Field(..., description="Product ID this document belongs to")
    document_name: str = Field(..., min_length=1, max_length=255, description="User-friendly document name")
    document_type: str = Field(
        "vision",
        description="Document category: vision, architecture, features, setup, api, testing, deployment, custom"
    )
    content: Optional[str] = Field(None, description="Inline document content (for inline or hybrid storage)")
    storage_type: str = Field("inline", description="Storage mode: file, inline, hybrid")
    auto_chunk: bool = Field(True, description="Automatically chunk document after creation")
    display_order: int = Field(0, description="Display order in UI (lower numbers first)")
    version: str = Field("1.0.0", description="Semantic version")

    model_config = ConfigDict(from_attributes=True)


class VisionDocumentUpdate(BaseModel):
    """
    Schema for updating vision document content.

    Updating content automatically:
    - Recalculates content hash
    - Resets chunked flag to False
    - Triggers re-chunking if auto_rechunk=True
    """
    content: str = Field(..., description="New document content")
    auto_rechunk: bool = Field(True, description="Automatically re-chunk after update")

    model_config = ConfigDict(from_attributes=True)


class VisionDocumentResponse(BaseModel):
    """
    Full vision document response with all fields.

    Returned from:
    - GET /vision-documents/product/{product_id}
    - POST /vision-documents/
    - PUT /vision-documents/{document_id}
    """
    id: str = Field(..., description="Vision document ID")
    tenant_key: str = Field(..., description="Tenant key (multi-tenant isolation)")
    product_id: str = Field(..., description="Product ID")
    document_name: str = Field(..., description="Document name")
    document_type: str = Field(..., description="Document category")
    storage_type: str = Field(..., description="Storage mode: file, inline, hybrid")
    vision_path: Optional[str] = Field(None, description="File path (if file-based storage)")
    vision_document: Optional[str] = Field(None, description="Inline content (if inline storage)")
    chunked: bool = Field(..., description="Has document been chunked")
    chunk_count: int = Field(..., description="Number of chunks created")
    total_tokens: Optional[int] = Field(None, description="Estimated total tokens")
    content_hash: Optional[str] = Field(None, description="SHA-256 content hash")
    version: str = Field(..., description="Document version")
    is_active: bool = Field(..., description="Active status")
    display_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    chunked_at: Optional[datetime] = Field(None, description="Last chunking timestamp")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(from_attributes=True)


class RechunkRequest(BaseModel):
    """
    Schema for triggering re-chunking (POST /vision-documents/{document_id}/rechunk).

    Re-chunking:
    - Deletes existing chunks for this document
    - Chunks content using EnhancedChunker
    - Updates vision document metadata (chunked=True, chunk_count, total_tokens)
    """
    # No fields - just a trigger endpoint
    pass


class RechunkResponse(BaseModel):
    """
    Response from re-chunking operation.
    """
    success: bool = Field(..., description="Whether re-chunking succeeded")
    document_id: str = Field(..., description="Document ID that was re-chunked")
    document_name: str = Field(..., description="Document name")
    chunks_created: int = Field(..., description="Number of chunks created")
    total_tokens: int = Field(..., description="Total estimated tokens")
    old_chunks_deleted: int = Field(..., description="Number of old chunks deleted")

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    """
    Response from vision document deletion.

    Deletion cascades:
    - Deletes vision document
    - Cascades to delete all chunks (via MCPContextIndex.vision_document_id)
    """
    success: bool = Field(..., description="Whether deletion succeeded")
    document_id: str = Field(..., description="Deleted document ID")
    document_name: str = Field(..., description="Deleted document name")
    chunks_deleted: int = Field(..., description="Number of chunks deleted (CASCADE)")

    model_config = ConfigDict(from_attributes=True)

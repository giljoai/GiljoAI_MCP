"""
Pydantic Models for Product Endpoints - Handover 0126

Request/response models for product operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Request model for creating a product"""

    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    project_path: Optional[str] = Field(
        None, description="File system path to product folder (required for agent export)"
    )


class ProductUpdate(BaseModel):
    """Request model for updating a product"""

    name: Optional[str] = None
    description: Optional[str] = None
    project_path: Optional[str] = None


class ProductResponse(BaseModel):
    """Response model for product operations"""

    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
    unresolved_tasks: int = 0
    unfinished_projects: int = 0
    vision_documents_count: int = 0
    config_data: Optional[dict] = Field(None, description="Rich configuration data")
    has_config_data: bool = Field(False, description="Whether product has config_data populated")
    is_active: bool = Field(False, description="Whether this product is currently active")
    project_path: Optional[str] = Field(
        None, description="File system path to product folder (required for agent export)"
    )


class ActiveProductInfo(BaseModel):
    """Minimal active product info for efficient responses"""

    id: str
    name: str
    description: Optional[str]
    activated_at: datetime = Field(description="When this product was activated")
    active_projects_count: int = Field(default=0, description="Number of active projects")


class ProductActivationResponse(ProductResponse):
    """Enhanced response for product activation with context"""

    previous_active_product: Optional[ActiveProductInfo] = Field(
        None, description="Previously active product (if any) that was deactivated"
    )
    activation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="When this activation occurred"
    )


class ProductDeleteResponse(BaseModel):
    """Enhanced response for product deletion"""

    message: str
    deleted_product_id: str
    was_active: bool = Field(description="Whether the deleted product was active")
    remaining_products_count: int
    new_active_product: Optional[ActiveProductInfo] = Field(
        None, description="Auto-activated product (if deleted product was active)"
    )


class ActiveProductRefreshResponse(BaseModel):
    """Response for /refresh-active endpoint"""

    active_product: Optional[ActiveProductInfo]
    total_products_count: Optional[int] = None
    last_refreshed_at: Optional[datetime] = None


class DeletedProductResponse(BaseModel):
    """Response model for deleted products list"""

    id: str
    name: str
    description: Optional[str]
    deleted_at: datetime
    days_until_purge: int = Field(ge=0, description="Days remaining before permanent deletion")
    purge_date: datetime = Field(description="Date when product will be permanently deleted")
    project_count: int = Field(ge=0, description="Total projects under this product")
    vision_documents_count: int = Field(ge=0, description="Total vision documents")


class VisionChunk(BaseModel):
    """Response model for vision document chunks"""

    chunk_number: int
    total_chunks: int
    content: str
    char_start: int
    char_end: int
    boundary_type: str
    keywords: List[str]
    headers: List[str]


class TokenEstimateResponse(BaseModel):
    """Token estimation response for active product"""

    product_id: str = Field(..., description="Active product ID")
    product_name: str = Field(..., description="Active product name")
    field_tokens: Dict[str, int] = Field(..., description="Token count per prioritized field")
    total_field_tokens: int = Field(..., description="Sum of all field tokens")
    overhead_tokens: int = Field(..., description="Fixed overhead for mission structure")
    total_tokens: int = Field(..., description="Total tokens (field_tokens + overhead)")
    token_budget: int = Field(..., description="User's configured token budget")
    percentage_used: float = Field(..., description="Percentage of budget used")


class CascadeImpact(BaseModel):
    """Cascade impact response for product deletion"""

    product_id: str
    projects_count: int = Field(..., description="Total number of projects")
    unfinished_projects: int = Field(..., description="Number of unfinished projects")
    tasks_count: int = Field(..., description="Total number of tasks")
    unresolved_tasks: int = Field(..., description="Number of unresolved tasks")
    vision_documents_count: int = Field(..., description="Number of vision documents")
    total_chunks: int = Field(..., description="Total number of context chunks")

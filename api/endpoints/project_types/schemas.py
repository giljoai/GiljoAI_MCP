"""
Pydantic schemas for Project Type taxonomy endpoints - Handover 0440a Phase 2

Schemas:
- ProjectTypeCreate: Validated input for creating a new project type
- ProjectTypeUpdate: Partial update (label, color, sort_order only)
- ProjectTypeResponse: Full response model with project_count
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectTypeCreate(BaseModel):
    """Request model for creating a project type."""

    abbreviation: str = Field(
        ...,
        min_length=2,
        max_length=4,
        pattern=r"^[A-Z]+$",
        description="2-4 uppercase letter abbreviation (e.g., BE, FE, API)",
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Human-readable label (e.g., Backend, Frontend)",
    )
    color: str = Field(
        default="#607D8B",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color for UI display",
    )
    sort_order: int = Field(default=0, description="Display ordering in UI dropdowns")


class ProjectTypeUpdate(BaseModel):
    """Request model for updating a project type (partial)."""

    label: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: Optional[int] = None


class ProjectTypeResponse(BaseModel):
    """Response model for project type details."""

    id: str
    tenant_key: str
    abbreviation: str
    label: str
    color: str
    sort_order: int
    project_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

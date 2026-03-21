"""
Product Context Tuning Endpoints - Handover 0831

Handles tuning prompt generation, proposal retrieval, and proposal actions
for on-demand product context drift detection.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.product_tuning_service import ProductTuningService

from .dependencies import get_db_manager


logger = logging.getLogger(__name__)
router = APIRouter()


# --- Request/Response Models ---


class GeneratePromptRequest(BaseModel):
    sections: list[str] = Field(..., description="Section keys to include in tuning prompt")


class GeneratePromptResponse(BaseModel):
    prompt: str
    sections_included: list[str]
    lookback_depth: int
    git_enabled: bool


class ProposalActionRequest(BaseModel):
    action: str = Field(..., description="accept, edit, or dismiss")
    value: str | None = Field(None, description="Override value for edit action")


class ProposalActionResponse(BaseModel):
    success: bool
    section: str
    action: str
    remaining_proposals: int


class EligibleSectionsResponse(BaseModel):
    sections: list[str]


# --- Helper ---


def _validate_product_id(product_id: str) -> None:
    """Validate product_id UUID format."""
    try:
        UUID(product_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid product_id format") from e


async def _get_tuning_service(current_user: User, db_manager) -> ProductTuningService:
    """Create a ProductTuningService with WebSocket manager from app state."""
    from api.app import state

    ws_manager = getattr(state, "websocket_manager", None)
    return ProductTuningService(
        db_manager=db_manager,
        tenant_key=current_user.tenant_key,
        websocket_manager=ws_manager,
    )


# --- Endpoints ---


@router.get("/{product_id}/tuning/sections")
async def get_eligible_sections(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> EligibleSectionsResponse:
    """Get sections eligible for tuning based on user's context toggle settings."""
    _validate_product_id(product_id)

    try:
        service = await _get_tuning_service(current_user, db_manager)
        sections = await service.get_eligible_sections(product_id, current_user.id)
        return EligibleSectionsResponse(sections=sections)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{product_id}/tuning/generate-prompt")
async def generate_tuning_prompt(
    product_id: str,
    request: GeneratePromptRequest,
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> GeneratePromptResponse:
    """
    Generate a tuning comparison prompt for selected sections.

    The prompt includes current product context and recent 360 memory entries
    at the user's configured depth. User copies this to their CLI tool.
    """
    _validate_product_id(product_id)

    try:
        service = await _get_tuning_service(current_user, db_manager)
        result = await service.assemble_tuning_prompt(
            product_id=product_id,
            user_id=current_user.id,
            sections=request.sections,
        )
        return GeneratePromptResponse(**result)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{product_id}/tuning/proposals")
async def get_proposals(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> dict[str, Any]:
    """Get current pending tuning proposals for a product."""
    _validate_product_id(product_id)

    try:
        service = await _get_tuning_service(current_user, db_manager)
        proposals = await service.get_proposals(product_id)
        return {"proposals": proposals}
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{product_id}/tuning/proposals/{section}/apply")
async def apply_proposal(
    product_id: str,
    section: str,
    request: ProposalActionRequest,
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> ProposalActionResponse:
    """
    Apply, edit, or dismiss a single tuning proposal.

    Actions:
    - accept: Apply the proposed value to the product field
    - edit: Apply a user-provided value instead
    - dismiss: Remove the proposal without changes
    """
    _validate_product_id(product_id)

    try:
        service = await _get_tuning_service(current_user, db_manager)
        result = await service.apply_proposal(
            product_id=product_id,
            section=section,
            action=request.action,
            value=request.value,
        )
        return ProposalActionResponse(**result)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{product_id}/tuning/dismiss-all")
async def dismiss_all_proposals(
    product_id: str,
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> dict[str, Any]:
    """Clear all pending proposals and update last_tuned_at."""
    _validate_product_id(product_id)

    try:
        service = await _get_tuning_service(current_user, db_manager)
        result = await service.clear_review(product_id)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

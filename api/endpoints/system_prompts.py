"""Admin-only system prompt management endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.giljo_mcp.auth.dependencies import require_admin
from src.giljo_mcp.models import User


router = APIRouter()


class OrchestratorPromptResponse(BaseModel):
    content: str = Field(..., description="Full orchestrator prompt content")
    is_override: bool = Field(..., description="True when an admin override is active")
    updated_at: datetime | None = Field(None, description="Override timestamp (if applicable)")
    updated_by: str | None = Field(None, description="Identifier for the admin who last updated the prompt")


class OrchestratorPromptUpdateRequest(BaseModel):
    content: str = Field(..., description="Replacement prompt content")


@router.get("/orchestrator-prompt", response_model=OrchestratorPromptResponse)
async def get_orchestrator_prompt(current_user: User = Depends(require_admin)):
    """Return the current orchestrator prompt (default or override)."""
    # Lazy import to avoid circular dependency
    from api.app import state

    service = state.system_prompt_service
    if not service:
        raise HTTPException(status_code=503, detail="System prompt service not available")

    prompt = await service.get_orchestrator_prompt()
    return OrchestratorPromptResponse(
        content=prompt.content,
        is_override=prompt.is_override,
        updated_at=prompt.updated_at,
        updated_by=prompt.updated_by,
    )


@router.put("/orchestrator-prompt", response_model=OrchestratorPromptResponse)
async def update_orchestrator_prompt(
    payload: OrchestratorPromptUpdateRequest, current_user: User = Depends(require_admin)
):
    """Persist an admin override for the orchestrator prompt."""
    # Lazy import to avoid circular dependency
    from api.app import state

    service = state.system_prompt_service
    if not service:
        raise HTTPException(status_code=503, detail="System prompt service not available")

    try:
        prompt = await service.update_orchestrator_prompt(
            content=payload.content, updated_by=current_user.email or current_user.username or current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return OrchestratorPromptResponse(
        content=prompt.content,
        is_override=prompt.is_override,
        updated_at=prompt.updated_at,
        updated_by=prompt.updated_by,
    )


@router.post("/orchestrator-prompt/reset", response_model=OrchestratorPromptResponse)
async def reset_orchestrator_prompt(current_user: User = Depends(require_admin)):
    """Remove the override and restore the default prompt."""
    # Lazy import to avoid circular dependency
    from api.app import state

    service = state.system_prompt_service
    if not service:
        raise HTTPException(status_code=503, detail="System prompt service not available")

    prompt = await service.reset_orchestrator_prompt()
    return OrchestratorPromptResponse(
        content=prompt.content,
        is_override=prompt.is_override,
        updated_at=prompt.updated_at,
        updated_by=prompt.updated_by,
    )

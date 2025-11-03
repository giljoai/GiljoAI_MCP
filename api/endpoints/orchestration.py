"""
Orchestration API Endpoints - Mission Regeneration

Handover 0086B Task 3.3
Created: 2025-11-02
"""

import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Product, Project, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["orchestration"])


class RegenerateMissionRequest(BaseModel):
    project_id: UUID
    override_field_priorities: Optional[Dict[str, int]] = None
    override_serena_enabled: Optional[bool] = None


class RegenerateMissionResponse(BaseModel):
    mission: str
    token_estimate: int
    user_config_applied: bool
    serena_enabled: bool
    field_priorities_used: Dict[str, int]


async def _get_user_config_with_overrides(
    user_id: UUID,
    db: AsyncSession,
    override_priorities: Optional[Dict[str, int]],
    override_serena: Optional[bool],
) -> Dict:
    from sqlalchemy import select
    result = await db.execute(select(User).filter_by(id=user_id))
    user = result.scalar_one_or_none()

    base_config = {
        "field_priorities": {},
        "serena_enabled": False,
        "token_budget": 2000,
    }

    if user and user.field_priority_config:
        base_config["field_priorities"] = user.field_priority_config.get("field_priorities", {})
        base_config["serena_enabled"] = user.field_priority_config.get("serena_enabled", False)
        base_config["token_budget"] = user.field_priority_config.get("token_budget", 2000)

    if override_priorities is not None:
        base_config["field_priorities"] = {**base_config["field_priorities"], **override_priorities}
    if override_serena is not None:
        base_config["serena_enabled"] = override_serena

    return base_config


@router.post("/regenerate-mission", response_model=RegenerateMissionResponse)
async def regenerate_mission(
    request: RegenerateMissionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
):
    logger.info(f"Mission regeneration requested for project {request.project_id}")

    from sqlalchemy import select
    result = await db.execute(
        select(Project).filter_by(id=request.project_id, tenant_key=current_user.tenant_key)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(Product).filter_by(id=project.product_id, tenant_key=current_user.tenant_key)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    user_config = await _get_user_config_with_overrides(
        user_id=current_user.id,
        db=db,
        override_priorities=request.override_field_priorities,
        override_serena=request.override_serena_enabled,
    )

    mission_text = f"Mission for {project.name}: {project.mission}"
    token_estimate = len(mission_text) // 4

    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="project:mission_updated",
            data={
                "project_id": str(request.project_id),
                "tenant_key": current_user.tenant_key,
                "mission": mission_text,
                "token_estimate": token_estimate,
                "generated_by": "user",
                "user_config_applied": True,
                "field_priorities": user_config["field_priorities"],
            },
        )
    except Exception as e:
        logger.error(f"Failed to broadcast: {e}")

    return RegenerateMissionResponse(
        mission=mission_text,
        token_estimate=token_estimate,
        user_config_applied=True,
        serena_enabled=user_config["serena_enabled"],
        field_priorities_used=user_config["field_priorities"],
    )

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Settings API endpoints for GiljoAI MCP.

Provides REST API for system settings management:
- GET/PUT /general - General system settings
- GET /database - Database settings (read-only)

All endpoints enforce multi-tenant isolation and role-based access control.
Handover 0506: Settings endpoints implementation.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin, require_ce_mode
from giljo_mcp.models import User
from giljo_mcp.services.settings_service import SettingsService, SystemSettingsService
from giljo_mcp.services.silence_detector import DEFAULT_SILENCE_THRESHOLD_MINUTES
from giljo_mcp.utils.log_sanitizer import sanitize


logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic Models


class SettingsUpdate(BaseModel):
    """Settings update request - settings dict required"""

    settings: dict[str, Any]


class SettingsResponse(BaseModel):
    """Settings response - wraps settings dict"""

    settings: dict[str, Any]


class SettingsUpdateResponse(BaseModel):
    """Settings update response - includes success message"""

    settings: dict[str, Any]
    message: str


class AgentSilenceThresholdUpdate(BaseModel):
    """Update request for the deployment-wide agent silence threshold."""

    agent_silence_threshold_minutes: int = Field(ge=1)


class AgentSilenceThresholdResponse(BaseModel):
    """Deployment-wide agent silence threshold response."""

    agent_silence_threshold_minutes: int


class AgentSilenceThresholdUpdateResponse(AgentSilenceThresholdResponse):
    """Deployment-wide agent silence threshold update response."""

    message: str


# API Endpoints


@router.get(
    "/general",
    response_model=SettingsResponse,
    summary="Get general settings",
    description="Get general system settings for current tenant",
)
async def get_general_settings(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> SettingsResponse:
    """Get general settings - accessible to all authenticated users"""
    logger.debug("User %s retrieving general settings", sanitize(current_user.username))

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.get_settings("general")

    return SettingsResponse(settings=settings)


# TENANT-LEVEL
@router.put(
    "/general",
    response_model=SettingsUpdateResponse,
    summary="Update general settings",
    description="Update general system settings (admin only)",
)
async def update_general_settings(
    request: SettingsUpdate, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db_session)
) -> SettingsUpdateResponse:
    """Update general settings - admin only"""
    logger.info("Admin %s updating general settings", sanitize(current_user.username))

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.update_settings("general", request.settings)

    return SettingsUpdateResponse(settings=settings, message="Settings updated successfully")


# SERVER-LEVEL: reads deployment-wide agent silence threshold from system_settings, CE-only.
@router.get(
    "/system/agent-silence-threshold",
    response_model=AgentSilenceThresholdResponse,
    summary="Get deployment-wide agent silence threshold",
    description="Get the server-global agent silence threshold in minutes",
)
async def get_agent_silence_threshold(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    _ce: None = Depends(require_ce_mode),
) -> AgentSilenceThresholdResponse:
    logger.debug("User %s retrieving agent silence threshold", sanitize(current_user.username))

    service = SystemSettingsService(db)
    threshold = await service.get_agent_silence_threshold_minutes()

    return AgentSilenceThresholdResponse(agent_silence_threshold_minutes=threshold or DEFAULT_SILENCE_THRESHOLD_MINUTES)


# SERVER-LEVEL: writes deployment-wide agent silence threshold to system_settings, CE-only.
@router.put(
    "/system/agent-silence-threshold",
    response_model=AgentSilenceThresholdUpdateResponse,
    summary="Update deployment-wide agent silence threshold",
    description="Update the server-global agent silence threshold in minutes (admin only)",
)
async def update_agent_silence_threshold(
    request: AgentSilenceThresholdUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _ce: None = Depends(require_ce_mode),
) -> AgentSilenceThresholdUpdateResponse:
    logger.info("Admin %s updating agent silence threshold", sanitize(current_user.username))

    service = SystemSettingsService(db)
    threshold = await service.update_agent_silence_threshold_minutes(request.agent_silence_threshold_minutes)

    return AgentSilenceThresholdUpdateResponse(
        agent_silence_threshold_minutes=threshold,
        message="Settings updated successfully",
    )


@router.get(
    "/database",
    response_model=SettingsResponse,
    summary="Get database settings",
    description="Get database configuration for current tenant (read-only)",
)
async def get_database_settings(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> SettingsResponse:
    """Get database settings - read-only for all authenticated users"""
    logger.debug("User %s retrieving database settings", sanitize(current_user.username))

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.get_settings("database")

    return SettingsResponse(settings=settings)

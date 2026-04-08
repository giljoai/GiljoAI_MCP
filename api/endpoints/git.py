# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Git integration endpoints for system-level configuration.
Similar to Serena integration, operates at config.yaml level.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from src.giljo_mcp._config_io import read_config, write_config
from src.giljo_mcp.auth.dependencies import get_current_active_user


logger = logging.getLogger(__name__)
router = APIRouter()


class GitToggleRequest(BaseModel):
    """Request to toggle Git integration."""

    enabled: bool


class GitSettingsRequest(BaseModel):
    """Request to update Git advanced settings."""

    use_in_prompts: bool
    include_commit_history: bool | None = True
    max_commits: int | None = 50
    branch_strategy: str | None = "main"


class GitToggleResponse(BaseModel):
    """Response from toggling Git integration."""

    success: bool
    enabled: bool
    message: str
    settings: dict[str, Any]


@router.post("/toggle", response_model=GitToggleResponse)
async def toggle_git_integration(
    request: GitToggleRequest,
    current_user=Depends(get_current_active_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> GitToggleResponse:
    """
    Toggle Git integration at the system level.
    Stores in config.yaml like Serena integration.
    """
    config = read_config()

    # Ensure features section exists
    if "features" not in config:
        config["features"] = {}

    # Ensure git_integration section exists with defaults
    if "git_integration" not in config["features"]:
        config["features"]["git_integration"] = {
            "enabled": False,
            "use_in_prompts": False,
            "include_commit_history": True,
            "max_commits": 50,
            "branch_strategy": "main",
        }

    # Update enabled status
    config["features"]["git_integration"]["enabled"] = request.enabled
    config["features"]["git_integration"]["use_in_prompts"] = request.enabled

    # Save config
    try:
        write_config(config)
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info(f"Git integration toggled to {request.enabled} by user {current_user.username}")

    # Emit WebSocket event for real-time UI updates
    try:
        tenant_key = current_user.tenant_key
        await ws_dep.broadcast_to_tenant(
            tenant_key=tenant_key,
            event_type="product:git:settings:changed",
            data={"enabled": request.enabled, "settings": config["features"]["git_integration"]},
        )
        logger.info(f"[WEBSOCKET] Broadcasted git integration change to tenant {tenant_key}")
    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
        logger.warning(f"[WEBSOCKET] Failed to broadcast git integration update: {ws_error}")

    return GitToggleResponse(
        success=True,
        enabled=request.enabled,
        message=f"Git integration {'enabled' if request.enabled else 'disabled'} successfully",
        settings=config["features"]["git_integration"],
    )


@router.post("/settings", response_model=GitToggleResponse)
async def update_git_settings(
    request: GitSettingsRequest, current_user=Depends(get_current_active_user)
) -> GitToggleResponse:
    """
    Update Git advanced settings at the system level.
    """
    config = read_config()

    # Ensure structure exists
    if "features" not in config:
        config["features"] = {}
    if "git_integration" not in config["features"]:
        config["features"]["git_integration"] = {}

    # Update settings
    git_settings = config["features"]["git_integration"]
    git_settings["use_in_prompts"] = request.use_in_prompts
    git_settings["include_commit_history"] = request.include_commit_history
    git_settings["max_commits"] = request.max_commits
    git_settings["branch_strategy"] = request.branch_strategy

    # Save config
    try:
        write_config(config)
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info(f"Git settings updated by user {current_user.username}")

    return GitToggleResponse(
        success=True,
        enabled=git_settings.get("enabled", False),
        message="Git settings updated successfully",
        settings=git_settings,
    )


@router.get("/settings")
async def get_git_settings(current_user=Depends(get_current_active_user)) -> dict[str, Any]:
    """
    Get current Git integration settings from config.
    """
    config = read_config()

    # Return settings or defaults
    if "features" in config and "git_integration" in config["features"]:
        return config["features"]["git_integration"]
    return {
        "enabled": False,
        "use_in_prompts": False,
        "include_commit_history": True,
        "max_commits": 50,
        "branch_strategy": "main",
    }

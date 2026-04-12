# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Simplified Serena MCP toggle endpoint (Handover 0277).

Provides single toggle for Serena MCP integration.
Removed advanced settings for 99% token reduction.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.giljo_mcp._config_io import read_config, write_config
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User


logger = logging.getLogger(__name__)
router = APIRouter()


class SerenaToggleRequest(BaseModel):
    """Request model for Serena toggle"""

    use_in_prompts: bool


@router.get("/settings")
async def get_serena_settings(current_user: User = Depends(get_current_active_user)):
    """
    Get simplified Serena MCP settings.

    Returns only use_in_prompts toggle (advanced settings removed in Handover 0277).
    """
    config = read_config()
    serena = config.get("features", {}).get("serena_mcp", {})

    return {"use_in_prompts": bool(serena.get("use_in_prompts", False))}


@router.post("/toggle")
async def toggle_serena(request: SerenaToggleRequest, current_user: User = Depends(get_current_active_user)):
    """
    Toggle Serena MCP on/off.

    Accepts only use_in_prompts boolean (advanced settings removed in Handover 0277).
    """
    config = read_config()

    # Ensure features section exists
    if "features" not in config:
        config["features"] = {}
    if "serena_mcp" not in config["features"]:
        config["features"]["serena_mcp"] = {}

    # Update flag
    config["features"]["serena_mcp"]["use_in_prompts"] = request.use_in_prompts

    try:
        write_config(config)
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    logger.info("Serena prompts %s", "enabled" if request.use_in_prompts else "disabled")

    # Return format expected by frontend (success, enabled, message)
    return {
        "success": True,
        "enabled": request.use_in_prompts,
        "use_in_prompts": request.use_in_prompts,  # Keep for backwards compatibility
        "message": f"Serena prompts {'enabled' if request.use_in_prompts else 'disabled'}",
    }


@router.get("/status")
async def get_serena_status(current_user: User = Depends(get_current_active_user)):
    """Get current Serena prompt toggle status (legacy endpoint)."""
    config = read_config()
    enabled = config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

    return {"enabled": enabled, "message": f"Serena prompts {'enabled' if enabled else 'disabled'}"}

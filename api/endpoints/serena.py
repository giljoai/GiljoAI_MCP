"""
Simplified Serena MCP toggle endpoint (Handover 0277).

Provides single toggle for Serena MCP integration.
Removed advanced settings for 99% token reduction.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)
router = APIRouter()


class SerenaToggleRequest(BaseModel):
    """Request model for Serena toggle"""

    use_in_prompts: bool


def get_config_path() -> Path:
    """Get path to config.yaml."""
    return Path.cwd() / "config.yaml"


def read_config() -> dict[str, Any]:
    """Read config.yaml."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, ValueError):
        logger.exception("Failed to read config")
        return {}


def write_config(config: dict[str, Any]) -> None:
    """Write config.yaml."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except (OSError, ValueError) as e:
        logger.exception("Failed to write config")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings")
async def get_serena_settings():
    """
    Get simplified Serena MCP settings.

    Returns only use_in_prompts toggle (advanced settings removed in Handover 0277).
    """
    config = read_config()
    serena = config.get("features", {}).get("serena_mcp", {})

    return {"use_in_prompts": bool(serena.get("use_in_prompts", False))}


@router.post("/toggle")
async def toggle_serena(request: SerenaToggleRequest):
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

    write_config(config)

    logger.info(f"Serena prompts {'enabled' if request.use_in_prompts else 'disabled'}")

    # Return format expected by frontend (success, enabled, message)
    return {
        "success": True,
        "enabled": request.use_in_prompts,
        "use_in_prompts": request.use_in_prompts,  # Keep for backwards compatibility
        "message": f"Serena prompts {'enabled' if request.use_in_prompts else 'disabled'}",
    }


@router.get("/status")
async def get_serena_status():
    """Get current Serena prompt toggle status (legacy endpoint)."""
    config = read_config()
    enabled = config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

    return {"enabled": enabled, "message": f"Serena prompts {'enabled' if enabled else 'disabled'}"}

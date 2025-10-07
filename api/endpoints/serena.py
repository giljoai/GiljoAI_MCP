"""Simple Serena MCP toggle endpoint."""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import APIRouter, HTTPException, Body

logger = logging.getLogger(__name__)
router = APIRouter()


def get_config_path() -> Path:
    """Get path to config.yaml."""
    return Path.cwd() / "config.yaml"


def read_config() -> Dict[str, Any]:
    """Read config.yaml."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to read config: {e}")
        return {}


def write_config(config: Dict[str, Any]) -> None:
    """Write config.yaml."""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle")
async def toggle_serena(enabled: bool = Body(..., embed=True)):
    """
    Toggle Serena prompt instructions on/off.

    This simply updates the config flag that controls whether
    Serena tool guidance is included in agent prompts.
    """
    try:
        config = read_config()

        # Ensure features section exists
        if "features" not in config:
            config["features"] = {}
        if "serena_mcp" not in config["features"]:
            config["features"]["serena_mcp"] = {}

        # Update flag
        config["features"]["serena_mcp"]["use_in_prompts"] = enabled

        write_config(config)

        logger.info(f"Serena prompts {'enabled' if enabled else 'disabled'}")

        return {
            "success": True,
            "enabled": enabled,
            "message": f"Serena prompt instructions {'enabled' if enabled else 'disabled'}"
        }

    except Exception as e:
        logger.exception("Failed to toggle Serena")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_serena_status():
    """Get current Serena prompt toggle status."""
    try:
        config = read_config()
        enabled = (config.get("features", {})
                         .get("serena_mcp", {})
                         .get("use_in_prompts", False))

        return {
            "enabled": enabled,
            "message": f"Serena prompts {'enabled' if enabled else 'disabled'}"
        }
    except Exception as e:
        logger.exception("Failed to get Serena status")
        raise HTTPException(status_code=500, detail=str(e))

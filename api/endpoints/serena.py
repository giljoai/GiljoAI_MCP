"""Simple Serena MCP toggle endpoint."""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import APIRouter, Body, HTTPException


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
            "message": f"Serena prompt instructions {'enabled' if enabled else 'disabled'}",
        }

    except Exception as e:
        logger.exception("Failed to toggle Serena")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_serena_status():
    """Get current Serena prompt toggle status."""
    try:
        config = read_config()
        enabled = config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

        return {"enabled": enabled, "message": f"Serena prompts {'enabled' if enabled else 'disabled'}"}
    except Exception as e:
        logger.exception("Failed to get Serena status")
        raise HTTPException(status_code=500, detail=str(e))


def _get_serena_config_with_defaults(base_config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a merged Serena config with defaults filled in."""
    features = base_config.get("features", {})
    serena = features.get("serena_mcp", {})

    # Defaults
    defaults = {
        "use_in_prompts": bool(serena.get("use_in_prompts", False)),
        "tailor_by_mission": serena.get("tailor_by_mission", True),
        "dynamic_catalog": serena.get("dynamic_catalog", True),
        "prefer_ranges": serena.get("prefer_ranges", True),
        "max_range_lines": serena.get("max_range_lines", 180),
        "context_halo": serena.get("context_halo", 12),
    }
    return defaults


@router.get("/config")
async def get_serena_config():
    """Get full Serena MCP config with defaults."""
    try:
        config = read_config()
        return _get_serena_config_with_defaults(config)
    except Exception as e:
        logger.exception("Failed to read Serena config")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_serena_config(payload: Dict[str, Any]):
    """Update Serena MCP config. Accepts partial updates.

    Allowed keys:
      - use_in_prompts: bool
      - tailor_by_mission: bool
      - dynamic_catalog: bool
      - prefer_ranges: bool
      - max_range_lines: int
      - context_halo: int
    """
    try:
        # Validate allowed keys and types
        allowed_types = {
            "use_in_prompts": bool,
            "tailor_by_mission": bool,
            "dynamic_catalog": bool,
            "prefer_ranges": bool,
            "max_range_lines": int,
            "context_halo": int,
        }

        unknown = [k for k in payload if k not in allowed_types]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown keys: {', '.join(unknown)}")

        for key, val in payload.items():
            expected = allowed_types[key]
            if expected is int:
                if not isinstance(val, int) or val <= 0:
                    raise HTTPException(status_code=400, detail=f"{key} must be a positive integer")
            elif expected is bool:
                if not isinstance(val, bool):
                    raise HTTPException(status_code=400, detail=f"{key} must be a boolean")

        config = read_config()
        if "features" not in config:
            config["features"] = {}
        if "serena_mcp" not in config["features"]:
            config["features"]["serena_mcp"] = {}

        serena = config["features"]["serena_mcp"]
        serena.update(payload)

        write_config(config)
        return _get_serena_config_with_defaults(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update Serena config")
        raise HTTPException(status_code=500, detail=str(e))

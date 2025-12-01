"""
Git integration endpoints for system-level configuration.
Similar to Serena integration, operates at config.yaml level.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import yaml

from src.giljo_mcp.auth.dependencies import get_current_user
from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency

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


class GitToggleRequest(BaseModel):
    """Request to toggle Git integration."""
    enabled: bool


class GitSettingsRequest(BaseModel):
    """Request to update Git advanced settings."""
    use_in_prompts: bool
    include_commit_history: Optional[bool] = True
    max_commits: Optional[int] = 50
    branch_strategy: Optional[str] = "main"


class GitToggleResponse(BaseModel):
    """Response from toggling Git integration."""
    success: bool
    enabled: bool
    message: str
    settings: Dict[str, Any]


@router.post("/toggle", response_model=GitToggleResponse)
async def toggle_git_integration(
    request: GitToggleRequest,
    current_user = Depends(get_current_user),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency)
) -> GitToggleResponse:
    """
    Toggle Git integration at the system level.
    Stores in config.yaml like Serena integration.
    """
    try:
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
                "branch_strategy": "main"
            }

        # Update enabled status
        config["features"]["git_integration"]["enabled"] = request.enabled
        config["features"]["git_integration"]["use_in_prompts"] = request.enabled

        # Save config
        write_config(config)

        logger.info(f"Git integration toggled to {request.enabled} by user {current_user.username}")

        # Emit WebSocket event for real-time UI updates
        try:
            tenant_key = current_user.get('tenant_key') if isinstance(current_user, dict) else current_user.tenant_key
            await ws_dep.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type="product:git:settings:changed",
                data={
                    "enabled": request.enabled,
                    "settings": config["features"]["git_integration"]
                }
            )
            logger.info(f"[WEBSOCKET] Broadcasted git integration change to tenant {tenant_key}")
        except Exception as ws_error:
            logger.warning(f"[WEBSOCKET] Failed to broadcast git integration update: {ws_error}")

        return GitToggleResponse(
            success=True,
            enabled=request.enabled,
            message=f"Git integration {'enabled' if request.enabled else 'disabled'} successfully",
            settings=config["features"]["git_integration"]
        )

    except Exception as e:
        logger.error(f"Failed to toggle Git integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings", response_model=GitToggleResponse)
async def update_git_settings(
    request: GitSettingsRequest,
    current_user: dict = Depends(get_current_user)
) -> GitToggleResponse:
    """
    Update Git advanced settings at the system level.
    """
    try:
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
        write_config(config)

        logger.info(f"Git settings updated by user {current_user['username']}")

        return GitToggleResponse(
            success=True,
            enabled=git_settings.get("enabled", False),
            message="Git settings updated successfully",
            settings=git_settings
        )

    except Exception as e:
        logger.error(f"Failed to update Git settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_git_settings(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current Git integration settings from config.
    """
    try:
        config = read_config()

        # Return settings or defaults
        if "features" in config and "git_integration" in config["features"]:
            return config["features"]["git_integration"]
        else:
            return {
                "enabled": False,
                "use_in_prompts": False,
                "include_commit_history": True,
                "max_commits": 50,
                "branch_strategy": "main"
            }

    except Exception as e:
        logger.error(f"Failed to get Git settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
"""
Setup wizard API endpoints.

Handles:
- AI tool detection (Claude Code, Cline, Cursor, etc.)
- MCP configuration generation
- Config file writing with user permission
- Connection testing
- Deployment mode configuration
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# Request/Response Models
class ToolDetectionResult(BaseModel):
    """Model for tool detection result."""

    id: str = Field(..., description="Tool identifier (e.g., 'claude_code')")
    name: str = Field(..., description="Human-readable tool name")
    detected: bool = Field(..., description="Whether tool is installed")
    version: Optional[str] = Field(None, description="Tool version if detected")
    path: Optional[str] = Field(None, description="Tool executable path")
    multi_agent: bool = Field(..., description="Whether tool supports multi-agent mode")


class MCPConfigRequest(BaseModel):
    """Request model for MCP config generation."""

    tool: str = Field(..., description="Tool name (e.g., 'Claude Code')")
    mode: str = Field(..., description="Deployment mode: localhost, lan, or wan")


class MCPRegistrationRequest(BaseModel):
    """Request model for MCP registration."""

    tool: str = Field(..., description="Tool name")
    config: Dict = Field(..., description="MCP configuration to write")


class MCPConnectionTestRequest(BaseModel):
    """Request model for MCP connection test."""

    tool: str = Field(..., description="Tool name to test")


class DeploymentModeRequest(BaseModel):
    """Request model for deployment mode configuration."""

    mode: str = Field(..., description="Deployment mode: localhost, lan, or wan")
    lan_ip: Optional[str] = Field(None, description="LAN IP address (required for LAN mode)")
    wan_url: Optional[str] = Field(None, description="WAN URL (required for WAN mode)")


# Tool detection functions
def check_tool_version(command: List[str], timeout: int = 5) -> Optional[str]:
    """
    Check if a tool is installed by running version command.

    Args:
        command: Command to execute (e.g., ['claude', 'code', '--version'])
        timeout: Command timeout in seconds

    Returns:
        Version string if tool is found, None otherwise
    """
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )

        if result.returncode == 0:
            return result.stdout.strip()

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def detect_claude_code() -> ToolDetectionResult:
    """Detect Claude Code installation."""
    version = check_tool_version(["claude", "code", "--version"])

    return ToolDetectionResult(
        id="claude_code",
        name="Claude Code",
        detected=version is not None,
        version=version,
        path=shutil.which("claude") if version else None,
        multi_agent=True,
    )


def detect_gemini_cli() -> ToolDetectionResult:
    """Detect Gemini CLI installation."""
    version = check_tool_version(["gemini-cli", "--version"])

    return ToolDetectionResult(
        id="gemini_cli",
        name="Gemini CLI",
        detected=version is not None,
        version=version,
        path=shutil.which("gemini-cli") if version else None,
        multi_agent=True,
    )


def detect_cursor() -> ToolDetectionResult:
    """Detect Cursor IDE installation."""
    # Check common Cursor paths
    cursor_paths = [
        shutil.which("cursor"),  # Linux/Mac
        Path.home() / "AppData" / "Local" / "Programs" / "cursor" / "Cursor.exe",  # Windows
        Path("/Applications/Cursor.app/Contents/MacOS/Cursor"),  # macOS
    ]

    detected_path = None
    for path in cursor_paths:
        if path and (isinstance(path, str) and Path(path).exists() or isinstance(path, Path) and path.exists()):
            detected_path = str(path)
            break

    return ToolDetectionResult(
        id="cursor",
        name="Cursor",
        detected=detected_path is not None,
        version=None,  # Cursor doesn't have a CLI version command
        path=detected_path,
        multi_agent=True,
    )


def detect_aider() -> ToolDetectionResult:
    """Detect Aider installation."""
    version = check_tool_version(["aider", "--version"])

    return ToolDetectionResult(
        id="aider",
        name="Aider",
        detected=version is not None,
        version=version,
        path=shutil.which("aider") if version else None,
        multi_agent=False,
    )


def detect_codex() -> ToolDetectionResult:
    """Detect Codex CLI installation."""
    version = check_tool_version(["codex", "--version"])

    return ToolDetectionResult(
        id="codex",
        name="Codex CLI",
        detected=version is not None,
        version=version,
        path=shutil.which("codex") if version else None,
        multi_agent=False,
    )


def detect_continue() -> ToolDetectionResult:
    """Detect Continue.dev installation."""
    # Continue is a VS Code extension, harder to detect
    # For now, mark as not detected unless we can check VS Code extensions
    return ToolDetectionResult(
        id="continue", name="Continue.dev", detected=False, version=None, path=None, multi_agent=True
    )


def detect_windsurf() -> ToolDetectionResult:
    """Detect Windsurf installation."""
    version = check_tool_version(["windsurf", "--version"])

    return ToolDetectionResult(
        id="windsurf",
        name="Windsurf",
        detected=version is not None,
        version=version,
        path=shutil.which("windsurf") if version else None,
        multi_agent=False,
    )


# MCP Config generation functions
def get_config():
    """Get GiljoAI MCP configuration."""
    # Import here to avoid circular imports
    from giljo_mcp.config_manager import get_config as get_config_singleton

    return get_config_singleton()


def get_lan_ip() -> str:
    """Get LAN IP address from config."""
    config = get_config()
    # Try to get from network section
    if hasattr(config, "network") and hasattr(config.network, "lan_ip"):
        return config.network.lan_ip

    # Fallback to localhost
    return "127.0.0.1"


def generate_claude_code_config(mode: str, lan_ip: Optional[str] = None, wan_url: Optional[str] = None) -> Dict:
    """
    Generate Claude Code MCP configuration.

    Args:
        mode: Deployment mode (localhost, lan, wan)
        lan_ip: LAN IP address (required for LAN mode)
        wan_url: WAN URL (required for WAN mode)

    Returns:
        MCP configuration dictionary
    """
    config = get_config()

    # Get venv python path
    venv_python = Path(config.paths.install_dir) / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Try Unix path
        venv_python = Path(config.paths.install_dir) / "venv" / "bin" / "python"

    # Base config
    mcp_config = {"command": str(venv_python), "args": ["-m", "giljo_mcp"], "env": {}}

    # Mode-specific environment
    if mode == "localhost":
        mcp_config["env"]["GILJO_API_URL"] = f"http://localhost:{config.services.api.port}"
    elif mode == "lan":
        if not lan_ip:
            lan_ip = get_lan_ip()
        mcp_config["env"]["GILJO_API_URL"] = f"http://{lan_ip}:{config.services.api.port}"
        # Add API key for LAN mode
        if hasattr(config, "security") and hasattr(config.security, "api_key"):
            mcp_config["env"]["GILJO_API_KEY"] = config.security.api_key
    elif mode == "wan":
        if not wan_url:
            raise HTTPException(status_code=400, detail="WAN URL is required for WAN mode")
        mcp_config["env"]["GILJO_API_URL"] = wan_url
        # Add API key for WAN mode
        if hasattr(config, "security") and hasattr(config.security, "api_key"):
            mcp_config["env"]["GILJO_API_KEY"] = config.security.api_key
    else:
        raise HTTPException(status_code=400, detail=f"Invalid deployment mode: {mode}")

    return {"mcpServers": {"giljo-mcp": mcp_config}}


def write_claude_config(config_data: Dict) -> Dict:
    """
    Write Claude Code configuration.

    Creates backup of existing config.
    Merges with existing mcpServers if present.

    Args:
        config_data: Configuration to write

    Returns:
        Success status with paths
    """
    config_path = Path.home() / ".claude.json"

    backup_path = None

    # Backup existing config
    if config_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_suffix(f".json.backup_{timestamp}")
        shutil.copy(config_path, backup_path)

        # Load and merge existing config
        try:
            with open(config_path, encoding="utf-8") as f:
                existing = json.load(f)

            # Merge mcpServers
            if "mcpServers" not in existing:
                existing["mcpServers"] = {}

            existing["mcpServers"].update(config_data["mcpServers"])
            final_config = existing
        except (json.JSONDecodeError, KeyError):
            # If existing config is invalid, use new config
            final_config = config_data
    else:
        final_config = config_data

    # Write updated config
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(final_config, f, indent=2)
    except PermissionError as e:
        raise HTTPException(status_code=500, detail=f"Permission denied writing config: {e}") from e

    return {
        "success": True,
        "config_path": str(config_path),
        "backup_path": str(backup_path) if backup_path else None,
    }


# API Endpoints
@router.get("/detect-tools", response_model=Dict[str, List[ToolDetectionResult]])
async def detect_tools() -> Dict[str, List[ToolDetectionResult]]:
    """
    Scan system for installed AI coding tools.

    Returns:
        Dictionary containing list of detected tools with their status
    """
    tools = [
        detect_claude_code(),
        detect_gemini_cli(),
        detect_cursor(),
        detect_aider(),
        detect_codex(),
        detect_continue(),
        detect_windsurf(),
    ]

    return {"tools": tools}


@router.post("/generate-mcp-config")
async def generate_mcp_config(request: MCPConfigRequest) -> Dict:
    """
    Generate MCP configuration for selected tool.

    Args:
        request: Configuration request with tool name and deployment mode

    Returns:
        Tool-specific MCP configuration JSON
    """
    tool = request.tool
    mode = request.mode

    if tool == "Claude Code":
        return generate_claude_code_config(mode)
    # Add other tools here (Gemini CLI, Cursor, etc.)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")


@router.post("/register-mcp")
async def register_mcp(request: MCPRegistrationRequest) -> Dict:
    """
    Register MCP server with AI tool.

    Writes config to tool-specific location.
    Requires user permission (frontend confirms).

    Args:
        request: Registration request with tool name and config

    Returns:
        Success status with config and backup paths
    """
    tool = request.tool
    config_data = request.config

    if tool == "Claude Code":
        return write_claude_config(config_data)
    # Add other tools here
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")


@router.post("/test-mcp-connection")
async def test_mcp_connection(request: MCPConnectionTestRequest) -> Dict:
    """
    Test MCP connection for given tool.

    Attempts to:
    1. Read tool's config
    2. Verify giljo-mcp is registered
    3. Validate configuration

    Args:
        request: Connection test request with tool name

    Returns:
        Success status and connection details
    """
    tool = request.tool

    if tool == "Claude Code":
        config_path = Path.home() / ".claude.json"

        if not config_path.exists():
            return {
                "success": False,
                "status": "error",
                "message": "Claude Code config not found. Please register MCP first.",
            }

        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)

            # Check if giljo-mcp is registered
            if "mcpServers" not in config_data or "giljo-mcp" not in config_data["mcpServers"]:
                return {
                    "success": False,
                    "status": "error",
                    "message": "giljo-mcp not found in Claude Code configuration",
                }

            return {"success": True, "status": "connected", "message": "giljo-mcp is registered in Claude Code"}

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid config file format: {e}") from e
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool}")


@router.post("/configure-deployment-mode")
async def configure_deployment_mode(request: DeploymentModeRequest) -> Dict:
    """
    Configure deployment mode (localhost/LAN/WAN).

    Args:
        request: Deployment mode configuration

    Returns:
        Configuration result with API URL
    """
    mode = request.mode
    config = get_config()

    if mode == "localhost":
        api_url = f"http://localhost:{config.services.api.port}"
        return {"success": True, "mode": "localhost", "api_url": api_url}

    elif mode == "lan":
        lan_ip = request.lan_ip or get_lan_ip()
        api_url = f"http://{lan_ip}:{config.services.api.port}"
        return {"success": True, "mode": "lan", "api_url": api_url, "lan_ip": lan_ip}

    elif mode == "wan":
        if not request.wan_url:
            raise HTTPException(status_code=400, detail="WAN URL is required for WAN mode")
        return {"success": True, "mode": "wan", "api_url": request.wan_url}

    else:
        raise HTTPException(status_code=400, detail=f"Invalid deployment mode: {mode}")


@router.post("/complete")
async def complete_setup() -> Dict:
    """
    Mark setup wizard as complete.

    Returns:
        Success status
    """
    # TODO: Update user profile or system config to mark setup as complete
    # For now, just return success
    return {"success": True, "setup_completed": True}


@router.get("/status")
async def get_setup_status() -> Dict:
    """
    Check if database is configured and setup is complete.

    Returns:
        Setup status including database configuration state
    """
    config = get_config()

    # Check if we're in setup mode
    setup_mode = getattr(config, 'setup_mode', False)

    # Check database configuration
    database_configured = False
    database_connected = False
    database_error = None

    # Check if database config exists
    if hasattr(config, 'database') and config.database:
        database_configured = bool(
            config.database.host and
            config.database.port and
            config.database.database_name and
            config.database.username
        )

        # If configured, try to connect
        if database_configured and not setup_mode:
            try:
                from giljo_mcp.database import DatabaseManager
                import os

                # Try to get database URL
                db_url = os.getenv("DATABASE_URL")
                if not db_url and config.database.type == "postgresql":
                    db_url = f"postgresql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database_name}"

                if db_url:
                    db_manager = DatabaseManager(db_url, is_async=False)
                    with db_manager.get_session() as session:
                        # Test query
                        result = session.execute("SELECT 1")
                        result.fetchone()
                    database_connected = True
            except Exception as e:
                database_error = str(e)

    # Check if setup is complete (not in setup mode and database is connected)
    setup_complete = database_configured and database_connected and not setup_mode

    return {
        "setup_mode": setup_mode,
        "setup_complete": setup_complete,
        "database_configured": database_configured,
        "database_connected": database_connected,
        "database_error": database_error,
        "requires_setup": not setup_complete,
        "mode": getattr(config, 'mode', 'unknown'),
        "version": "1.0.0"
    }


@router.post("/reset", include_in_schema=False)
async def reset_setup() -> Dict:
    """
    Reset setup mode (development only).

    This endpoint is only available in development mode and allows
    resetting the system to setup mode for testing purposes.

    Returns:
        Reset status
    """
    config = get_config()

    # Only allow in development/localhost mode
    if getattr(config, 'mode', 'unknown') not in ['localhost', 'development']:
        raise HTTPException(
            status_code=403,
            detail="Reset is only available in development mode"
        )

    # Set setup mode flag
    config.setup_mode = True

    # Write updated config back
    try:
        import yaml
        config_path = Path.cwd() / "config.yaml"

        # Load existing config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {}

        # Add setup_mode flag
        config_data['setup_mode'] = True

        # Write back
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        return {
            "success": True,
            "message": "Setup mode reset. Restart the API server to enter setup mode.",
            "setup_mode": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset setup mode: {e}") from e


@router.get("/test-database")
async def test_database() -> Dict:
    """
    Test database connection.

    Returns:
        Database connection status
    """
    # Import here to avoid circular imports
    from giljo_mcp.database import DatabaseManager

    try:
        db_manager = DatabaseManager()
        # Try to execute a simple query
        with db_manager.get_session() as session:
            # Test query
            result = session.execute("SELECT 1")
            result.fetchone()

        config = get_config()
        return {
            "success": True,
            "database": config.database.name if hasattr(config, "database") else "giljo_mcp",
            "host": config.database.host if hasattr(config, "database") else "localhost",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}") from e

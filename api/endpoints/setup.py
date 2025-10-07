"""
Setup wizard API endpoints for first-time configuration.

These endpoints track setup completion status and tool attachment.
The database is always configured by the CLI installer, so these
endpoints focus on tracking wizard completion and MCP tool registration.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

# Import SetupStateManager for hybrid file/database state tracking
from src.giljo_mcp.setup.state_manager import SetupStateManager


logger = logging.getLogger(__name__)
router = APIRouter()


class NetworkMode(str, Enum):
    """Valid network deployment modes"""

    LOCALHOST = "localhost"
    LAN = "lan"
    WAN = "wan"


class LANConfig(BaseModel):
    """LAN-specific configuration settings"""

    server_ip: str = Field(..., description="Server IP address on LAN")
    firewall_configured: bool = Field(False, description="Whether firewall rules are configured")
    admin_username: str = Field("admin", description="Admin username for server mode")
    admin_password: str = Field(..., description="Admin password for server mode (will be hashed)")
    hostname: str = Field("giljo.local", description="Hostname for LAN access")


class SetupCompleteRequest(BaseModel):
    """Request model for setup completion"""

    tools_attached: list[str] = Field(
        default_factory=list, description="List of MCP tools that have been attached (e.g., ['claude-code'])"
    )
    network_mode: NetworkMode = Field(..., description="Network deployment mode (localhost, lan, or wan)")
    serena_enabled: bool = Field(False, description="Whether Serena MCP instructions are enabled")
    lan_config: Optional[LANConfig] = Field(None, description="LAN-specific configuration (optional)")

    @field_validator("network_mode")
    @classmethod
    def validate_network_mode(cls, v):
        """Ensure network_mode is valid"""
        if isinstance(v, str):
            try:
                return NetworkMode(v)
            except ValueError:
                valid_modes = [mode.value for mode in NetworkMode]
                raise ValueError(f"network_mode must be one of: {valid_modes}")
        return v


class SetupStatusResponse(BaseModel):
    """Response model for setup status"""

    completed: bool = Field(..., description="Whether setup wizard has been completed")
    database_configured: bool = Field(..., description="Whether database is configured (always true)")
    tools_attached: list[str] = Field(default_factory=list, description="List of attached MCP tools")
    network_mode: str = Field(..., description="Current network deployment mode")


class SetupCompleteResponse(BaseModel):
    """Response model for setup completion"""

    success: bool = Field(..., description="Whether setup completion was successful")
    message: str = Field(..., description="Human-readable status message")
    api_key: Optional[str] = Field(None, description="Generated API key for LAN/WAN modes")
    requires_restart: bool = Field(False, description="Whether service restart is required")


class McpConfigRequest(BaseModel):
    """Request model for MCP configuration generation"""

    tool: str = Field(..., description="Tool name (e.g., 'Claude Code')")
    mode: NetworkMode = Field(..., description="Deployment mode (localhost, lan, or wan)")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration"""

    mcpServers: dict[str, Any] = Field(..., description="MCP server configuration")


class RegisterMcpRequest(BaseModel):
    """Request model for MCP registration"""

    tool: str = Field(..., description="Tool name")
    config: dict[str, Any] = Field(..., description="MCP configuration to register")


class RegisterMcpResponse(BaseModel):
    """Response model for MCP registration"""

    success: bool = Field(..., description="Whether registration was successful")
    message: str = Field(..., description="Human-readable status message")
    config_path: Optional[str] = Field(None, description="Path to configuration file")
    backup_path: Optional[str] = Field(None, description="Path to backup file")


def get_config_path() -> Path:
    """Get path to config.yaml file - relative to project root"""
    # __file__ is api/endpoints/setup.py, go up to project root
    return Path(__file__).parent.parent.parent / "config.yaml"


def read_config() -> dict[str, Any]:
    """Read configuration from config.yaml"""
    config_path = get_config_path()

    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}")
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to read config.yaml: {e}")
        return {}


def write_config(config: dict[str, Any]) -> None:
    """Write configuration to config.yaml"""
    config_path = get_config_path()

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated config.yaml at {config_path}")
    except Exception as e:
        logger.error(f"Failed to write config.yaml: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {e}")


def update_cors_origins(config: dict[str, Any], server_ip: str, hostname: str = None) -> None:
    """
    Update CORS origins with LAN IP and hostname for network accessibility.

    Args:
        config: Configuration dictionary to update
        server_ip: Server IP address on LAN
        hostname: Optional hostname for LAN access
    """
    # Ensure security section exists
    if "security" not in config:
        config["security"] = {}
    if "cors" not in config["security"]:
        config["security"]["cors"] = {}
    if "allowed_origins" not in config["security"]["cors"]:
        config["security"]["cors"]["allowed_origins"] = []

    # Get frontend port from config
    frontend_port = config.get("services", {}).get("frontend", {}).get("port", 7274)

    # Get current origins
    origins = config["security"]["cors"]["allowed_origins"]

    # Add server IP origin
    server_origin = f"http://{server_ip}:{frontend_port}"
    if server_origin not in origins:
        origins.append(server_origin)
        logger.info(f"Added CORS origin: {server_origin}")

    # Add hostname origin if provided
    if hostname:
        hostname_origin = f"http://{hostname}:{frontend_port}"
        if hostname_origin not in origins:
            origins.append(hostname_origin)
            logger.info(f"Added CORS origin: {hostname_origin}")

    # Update config
    config["security"]["cors"]["allowed_origins"] = origins


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """
    Get setup completion status.

    Returns the current state of the setup wizard, including:
    - Whether setup has been completed
    - Database configuration status (always true - configured by installer)
    - List of attached MCP tools
    - Current network deployment mode

    The database is always configured by the CLI installer in Phase 0,
    so database_configured will always be true.

    Now uses SetupStateManager for hybrid file/database state tracking.
    """
    try:
        # Get tenant_key (use "default" for single-tenant mode)
        tenant_key = "default"

        # Initialize SetupStateManager (will try database first, fall back to file)
        state_manager = SetupStateManager.get_instance(tenant_key=tenant_key)

        # Get state from SetupStateManager (hybrid storage)
        state = state_manager.get_state()

        # Also read config.yaml for network mode (still authoritative for deployment settings)
        config = read_config()
        installation_section = config.get("installation", {})
        network_mode = installation_section.get("mode", "localhost")

        # Database is always configured by CLI installer
        database_configured = True

        # Get completion status from state manager
        completed = state.get("completed", False)

        # Get attached tools from state manager
        tools_attached = state.get("tools_enabled", [])

        return SetupStatusResponse(
            completed=completed,
            database_configured=database_configured,
            tools_attached=tools_attached,
            network_mode=network_mode,
        )

    except Exception as e:
        logger.error(f"Error getting setup status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get setup status: {e}")


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(request_body: SetupCompleteRequest = Body(...), request: Request = None):
    """
    Mark setup as complete and save configuration.

    This endpoint is called when the user finishes the setup wizard.
    It saves the configuration choices and marks setup as complete.

    For LAN mode, this endpoint also:
    - Generates an API key
    - Stores admin account credentials (encrypted)
    - Updates CORS origins for network access
    - Configures API to bind to 0.0.0.0

    The endpoint is idempotent - calling it multiple times will not
    cause errors and will update the configuration each time.

    Now uses SetupStateManager for persistent state tracking with version support.

    Args:
        request_body: Setup completion request with tools and network configuration
        request: FastAPI Request object (to access app state)

    Returns:
        Success response with confirmation message and API key (for LAN mode)
    """
    try:
        # Get tenant_key (use "default" for single-tenant mode)
        tenant_key = "default"

        # Initialize SetupStateManager
        state_manager = SetupStateManager.get_instance(tenant_key=tenant_key)

        # Read current config
        config = read_config()

        # Ensure setup section exists
        if "setup" not in config:
            config["setup"] = {}

        # Update setup section
        config["setup"]["completed"] = True
        config["setup"]["tools_attached"] = request_body.tools_attached
        config["setup"]["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Update installation mode
        if "installation" not in config:
            config["installation"] = {}

        config["installation"]["mode"] = request_body.network_mode.value

        # Initialize response variables
        api_key = None
        requires_restart = False

        # Handle LAN mode configuration
        if request_body.lan_config and request_body.network_mode == NetworkMode.LAN:
            logger.info("Configuring LAN mode setup...")

            # 1. Update CORS origins for network access
            update_cors_origins(config, request_body.lan_config.server_ip, request_body.lan_config.hostname)

            # 2. Generate API key (requires AuthManager from app state)
            try:
                # Get auth manager from request app state
                auth_manager = None
                if request and hasattr(request.app, "state") and hasattr(request.app.state, "api_state"):
                    auth_manager = request.app.state.api_state.auth

                if auth_manager:
                    # Use get_or_create_api_key for idempotent behavior
                    # This ensures the same key is returned when re-running the wizard
                    api_key = auth_manager.get_or_create_api_key(name="LAN Setup Key", permissions=["*"])
                    logger.info("✅ API key ready for LAN mode (idempotent)")

                    # 3. Store admin account (encrypted)
                    password_to_store = request_body.lan_config.admin_password
                    logger.info(
                        f"DEBUG: Password length = {len(password_to_store)} chars, {len(password_to_store.encode('utf-8'))} bytes"
                    )
                    auth_manager.store_admin_account(
                        username=request_body.lan_config.admin_username, password=password_to_store
                    )
                    logger.info(f"✅ Stored admin account for user: {request_body.lan_config.admin_username}")
                else:
                    # AuthManager not available - this is a critical error for LAN mode
                    logger.error("❌ AuthManager not available - cannot configure LAN mode")
                    raise HTTPException(
                        status_code=500,
                        detail="Authentication system not initialized. Please restart the API server and try again.",
                    )
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(f"❌ Failed to configure LAN authentication: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to configure LAN authentication: {e}")

            # 4. Save LAN server configuration
            if "server" not in config:
                config["server"] = {}

            config["server"]["ip"] = request_body.lan_config.server_ip
            config["server"]["hostname"] = request_body.lan_config.hostname
            config["server"]["admin_user"] = request_body.lan_config.admin_username
            config["server"]["firewall_configured"] = request_body.lan_config.firewall_configured

            # 5. Set API host to bind to all interfaces
            if "services" not in config:
                config["services"] = {}
            if "api" not in config["services"]:
                config["services"]["api"] = {}

            config["services"]["api"]["host"] = "0.0.0.0"
            requires_restart = True

            # 6. Enable API key authentication for LAN mode
            if "features" not in config:
                config["features"] = {}
            config["features"]["api_keys_required"] = True
            config["features"]["multi_user"] = True
            logger.info("✅ LAN MODE: Enabled API key authentication (api_keys_required=True, multi_user=True)")

            logger.info("LAN mode configuration complete - restart required")

        # Update network configuration based on mode
        if "services" not in config:
            config["services"] = {}

        if "api" not in config["services"]:
            config["services"]["api"] = {}

        # Set API host based on mode
        if request_body.network_mode == NetworkMode.LOCALHOST:
            config["services"]["api"]["host"] = "127.0.0.1"
            # Disable API key authentication for localhost mode
            if "features" not in config:
                config["features"] = {}
            config["features"]["api_keys_required"] = False
            config["features"]["multi_user"] = False
            logger.info("Localhost mode: API key authentication disabled")
        elif request_body.network_mode == NetworkMode.LAN and not request_body.lan_config:
            # LAN mode without LAN config - use default
            config["services"]["api"]["host"] = "0.0.0.0"
            requires_restart = True
            # Enable API key authentication for LAN mode (no full config)
            if "features" not in config:
                config["features"] = {}
            config["features"]["api_keys_required"] = True
            config["features"]["multi_user"] = True
            logger.info("✅ LAN MODE: Enabled API key authentication (api_keys_required=True, multi_user=True)")

        # Toggle Serena MCP instructions if requested
        try:
            if "features" not in config:
                config["features"] = {}
            if "serena_mcp" not in config["features"]:
                config["features"]["serena_mcp"] = {}

            config["features"]["serena_mcp"]["use_in_prompts"] = request_body.serena_enabled
            logger.info(f"Serena prompts {'enabled' if request_body.serena_enabled else 'disabled'}")
        except Exception as e:
            logger.warning(f"Failed to set Serena prompts: {e}")
            # Non-fatal error, continue with setup completion

        # Save all configuration changes at once
        write_config(config)

        # SAVE STATE TO SETUPSTATEMANAGER (hybrid file/database storage)
        try:
            # Create config snapshot for rollback capability (convert to JSON-serializable)
            import json
            config_snapshot = json.loads(json.dumps(config, default=str))

            # Track configured features
            features_configured = {
                "database_configured": True,  # Always true (CLI installer)
                "api_keys_configured": request_body.network_mode == NetworkMode.LAN,
                "cors_configured": request_body.network_mode == NetworkMode.LAN,
                "serena_enabled": request_body.serena_enabled,
            }

            # Get version for tracking
            setup_version = config.get("installation", {}).get("version", "2.0.0")

            # Mark as completed with version tracking
            state_manager.mark_completed(
                setup_version=setup_version,
                config_snapshot=config_snapshot
            )

            # Update additional state fields
            state_manager.update_state(
                tools_enabled=request_body.tools_attached,
                features_configured=features_configured,
                install_mode=request_body.network_mode.value,
                validation_passed=True,
                validation_failures=[],
            )

            logger.info(
                f"✅ Setup state saved to SetupStateManager for tenant {tenant_key}"
            )

        except Exception as e:
            # Non-fatal - log but don't fail the setup
            logger.warning(
                f"Failed to save setup state to SetupStateManager: {e}. "
                "Setup completed but state tracking may be incomplete."
            )

        logger.info(
            f"Setup completed successfully: mode={request_body.network_mode.value}, "
            f"tools={len(request_body.tools_attached)}, serena={request_body.serena_enabled}"
        )

        # Build response message
        if request_body.network_mode == NetworkMode.LAN and api_key:
            message = "LAN setup completed. Please restart services and save your API key securely."
        else:
            message = "Setup completed successfully. Configuration has been saved."

        return SetupCompleteResponse(success=True, message=message, api_key=api_key, requires_restart=requires_restart)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing setup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to complete setup: {e}")


@router.post("/migrate")
async def migrate_setup_state():
    """
    Migrate setup state from old version to current version.

    This endpoint checks if the stored setup state version matches the current
    application version. If there's a mismatch, it migrates the state to the
    current version.

    Returns:
        Migration status and details
    """
    try:
        # Get tenant_key (use "default" for single-tenant mode)
        tenant_key = "default"

        # Get current version from config
        config = read_config()
        current_setup_version = config.get("installation", {}).get("version", "2.0.0")

        # PostgreSQL version (could be queried from database)
        # For now, use the configured version
        current_db_version = "18"  # PostgreSQL 18

        # Initialize SetupStateManager with current versions
        state_manager = SetupStateManager.get_instance(
            tenant_key=tenant_key,
            current_version=current_setup_version,
            required_db_version=current_db_version
        )

        # Check if migration is needed
        if not state_manager.requires_migration():
            state = state_manager.get_state()
            return {
                "message": "No migration needed",
                "migrated": False,
                "current_version": current_setup_version,
                "stored_version": state.get("setup_version"),
                "database_version": current_db_version,
            }

        # Perform migration
        logger.info(
            f"Migrating setup state to version {current_setup_version} "
            f"for tenant {tenant_key}"
        )

        state_manager.migrate_state(
            new_setup_version=current_setup_version,
            new_database_version=current_db_version
        )

        # Validate state after migration
        valid, failures = state_manager.validate_state()

        if not valid:
            logger.warning(
                f"Setup state validation failed after migration: {failures}"
            )
            return {
                "message": "State migrated with validation warnings",
                "migrated": True,
                "current_version": current_setup_version,
                "database_version": current_db_version,
                "validation_passed": False,
                "validation_failures": failures,
            }

        return {
            "message": "State migrated successfully",
            "migrated": True,
            "current_version": current_setup_version,
            "database_version": current_db_version,
            "validation_passed": True,
        }

    except ValueError as e:
        logger.error(f"Invalid version format during migration: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")


@router.post("/generate-mcp-config", response_model=McpConfigResponse)
async def generate_mcp_config(request: McpConfigRequest = Body(...)):
    """
    Generate MCP configuration for a specific tool and deployment mode.

    Creates the appropriate MCP server configuration based on the tool
    and deployment mode (localhost, LAN, or WAN).

    Args:
        request: MCP configuration request with tool name and mode

    Returns:
        Generated MCP configuration object
    """
    try:
        # Read current config to get API settings
        config = read_config()
        services = config.get("services", {})
        api_config = services.get("api", {})

        # Get API port (default 7272)
        api_port = api_config.get("port", 7272)

        # Get API host based on mode
        if request.mode == NetworkMode.LOCALHOST:
            api_host = "localhost"
        else:
            # For LAN/WAN, use the server IP from config
            server_config = config.get("server", {})
            api_host = server_config.get("ip", "localhost")

        # Get project root (venv is in project root)
        project_root = Path.cwd()
        venv_python = project_root / "venv" / "Scripts" / "python.exe"

        # If venv doesn't exist on Windows, try Unix path
        if not venv_python.exists():
            venv_python = project_root / "venv" / "bin" / "python"

        # Generate MCP configuration
        mcp_config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": str(venv_python),
                    "args": ["-m", "giljo_mcp"],
                    "env": {
                        "GILJO_MCP_HOME": str(project_root),
                        "GILJO_SERVER_URL": f"http://{api_host}:{api_port}",
                    },
                }
            }
        }

        logger.info(f"Generated MCP config for {request.tool} in {request.mode.value} mode")
        return McpConfigResponse(**mcp_config)

    except Exception as e:
        logger.error(f"Error generating MCP config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate MCP configuration: {e}")


@router.get("/check-mcp-configured")
async def check_mcp_configured():
    """
    Check if giljo-mcp is already configured in Claude Code.

    Returns:
        Configuration status including whether MCP server is configured
    """
    try:
        import json
        from pathlib import Path

        # Get Claude Code config path
        home = Path.home()
        claude_config_path = home / ".claude.json"

        if not claude_config_path.exists():
            return {
                "configured": False,
                "message": "Claude Code config file not found",
            }

        # Read config
        try:
            with open(claude_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read Claude config: {e}")
            return {
                "configured": False,
                "message": "Could not read Claude Code config file",
            }

        # Check if giljo-mcp is configured
        mcp_servers = config.get("mcpServers", {})
        giljo_configured = "giljo-mcp" in mcp_servers

        if giljo_configured:
            return {
                "configured": True,
                "message": "giljo-mcp is already configured in Claude Code",
                "config": mcp_servers["giljo-mcp"],
            }
        else:
            return {
                "configured": False,
                "message": "giljo-mcp not found in Claude Code configuration",
            }

    except Exception as e:
        logger.error(f"Error checking MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check MCP configuration: {e}")


@router.get("/installation-info")
async def get_installation_info():
    """
    Get installation directory and platform information for restart instructions.

    Returns:
        Installation path and platform details
    """
    try:
        import platform as platform_module

        # Get project root
        project_root = Path.cwd()

        # Detect platform
        system = platform_module.system().lower()
        if system == "windows":
            platform_name = "windows"
        elif system == "darwin":
            platform_name = "macos"
        else:
            platform_name = "linux"

        return {
            "installation_path": str(project_root),
            "platform": platform_name,
            "start_script": "start_giljo.bat" if platform_name == "windows" else "start_giljo.sh",
            "stop_script": "stop_giljo.bat" if platform_name == "windows" else "stop_giljo.sh",
        }

    except Exception as e:
        logger.error(f"Error getting installation info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get installation info: {e}")


@router.post("/register-mcp", response_model=RegisterMcpResponse)
async def register_mcp(request: RegisterMcpRequest = Body(...)):
    """
    Register MCP server with AI tool (writes to tool's config file).

    Currently supports Claude Code by writing to ~/.claude.json

    Args:
        request: MCP registration request with tool name and config

    Returns:
        Registration success response with config and backup paths
    """
    try:
        tool_lower = request.tool.lower()

        if "claude" in tool_lower:
            # Write to Claude Code config file
            import json
            from pathlib import Path

            # Get user home directory
            home = Path.home()
            claude_config_path = home / ".claude.json"

            # Read existing config or create new one
            existing_config = {}
            if claude_config_path.exists():
                try:
                    with open(claude_config_path, "r", encoding="utf-8") as f:
                        existing_config = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read existing config: {e}")

            # Check if giljo-mcp is already configured
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}

            # Check if already configured - if so, skip registration
            if "giljo-mcp" in existing_config["mcpServers"]:
                logger.info(f"giljo-mcp already configured in Claude Code, skipping registration")
                return RegisterMcpResponse(
                    success=True,
                    message=f"MCP server already configured for {request.tool}",
                    config_path=str(claude_config_path),
                    backup_path=None,
                )

            # Backup existing config before modifying
            backup_path = None
            if claude_config_path.exists():
                import shutil
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = home / f".claude.json.backup_{timestamp}"
                shutil.copy2(claude_config_path, backup_path)
                logger.info(f"Backed up existing config to {backup_path}")

            # Merge MCP servers
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}

            # Update with new config
            existing_config["mcpServers"].update(request.config.get("mcpServers", {}))

            # Write updated config
            with open(claude_config_path, "w", encoding="utf-8") as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)

            logger.info(f"Registered MCP server for {request.tool} at {claude_config_path}")

            return RegisterMcpResponse(
                success=True,
                message=f"MCP server registered for {request.tool}",
                config_path=str(claude_config_path),
                backup_path=str(backup_path) if backup_path else None,
            )

        else:
            # Tool not supported yet
            raise HTTPException(status_code=400, detail=f"MCP registration not yet supported for tool: {request.tool}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering MCP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register MCP configuration: {e}")

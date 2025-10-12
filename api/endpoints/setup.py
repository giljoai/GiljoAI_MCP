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


class DeploymentContext(str, Enum):
    """
    Deployment context - METADATA ONLY (v3.0 unified architecture).

    IMPORTANT: In v3.0, this enum does NOT affect server behavior.
    All deployments use identical configuration:
    - Server ALWAYS binds to 0.0.0.0 (firewall controls access)
    - Authentication ALWAYS enabled (auto-login for localhost clients)
    - Admin user created based on lan_config (not context)

    This enum is saved to config.yaml for informational purposes only:
    - Helps users understand their deployment context
    - Used in documentation and UI labels
    - Does NOT trigger different code paths

    Values:
    - localhost: Developer workstation (firewall allows localhost only)
    - lan: Team network (firewall configured for LAN access)
    - wan: Internet access (firewall configured for WAN access)

    The ONLY behavioral difference is:
    - Admin user creation depends on lan_config (not context)
    - CORS origins added based on lan_config (not context)
    """

    LOCALHOST = "localhost"  # Metadata: localhost-only deployment
    LAN = "lan"  # Metadata: LAN deployment (firewall configured)
    WAN = "wan"  # Metadata: WAN deployment (firewall configured)  # Internet access


class LANConfig(BaseModel):
    """LAN-specific configuration settings"""

    server_ip: str = Field(..., description="Server IP address on LAN")
    firewall_configured: bool = Field(False, description="Whether firewall rules are configured")
    admin_username: str = Field("admin", description="Admin username for server mode")
    admin_password: str = Field(..., description="Admin password for server mode (will be hashed)")
    hostname: str = Field("giljo.local", description="Hostname for LAN access")
    adapter_name: Optional[str] = Field(None, description="Network adapter name (e.g., 'Ethernet')")
    adapter_id: Optional[str] = Field(None, description="Network adapter ID/interface ID")


class SetupCompleteRequest(BaseModel):
    """Request model for setup completion"""

    tools_attached: list[str] = Field(
        default_factory=list, description="List of MCP tools that have been attached (e.g., ['claude-code'])"
    )
    deployment_context: DeploymentContext = Field(
        DeploymentContext.LOCALHOST,
        description="Deployment context (metadata only - doesn't affect server behavior in v3.0)",
    )
    serena_enabled: bool = Field(False, description="Whether Serena MCP instructions are enabled")
    lan_config: Optional[LANConfig] = Field(None, description="LAN-specific configuration (optional)")

    @field_validator("deployment_context")
    @classmethod
    def validate_deployment_context(cls, v):
        """Ensure deployment_context is valid"""
        if isinstance(v, str):
            try:
                return DeploymentContext(v)
            except ValueError:
                valid_contexts = [ctx.value for ctx in DeploymentContext]
                raise ValueError(f"deployment_context must be one of: {valid_contexts}")
        return v


class SetupStatusResponse(BaseModel):
    """Response model for setup status"""

    database_initialized: bool = Field(..., description="Whether database tables have been created and initialized")
    database_configured: bool = Field(..., description="Whether database is configured (always true)")
    tools_attached: list[str] = Field(default_factory=list, description="List of attached MCP tools")
    network_mode: str = Field(..., description="Current network deployment mode")
    default_password_active: bool = Field(default=False, description="Whether default admin password is still active")


class SetupCompleteResponse(BaseModel):
    """Response model for setup completion"""

    success: bool = Field(..., description="Whether setup completion was successful")
    message: str = Field(..., description="Human-readable status message")
    api_key: Optional[str] = Field(
        None, description="API key for tool integrations (created separately in Attach Tools step)"
    )
    requires_restart: bool = Field(False, description="Whether service restart is required")
    mode: Optional[str] = Field(None, description="Installation mode (localhost, lan, wan)")
    server_url: Optional[str] = Field(None, description="Server URL for API access")
    admin_username: Optional[str] = Field(None, description="Admin username (LAN/WAN modes only)")


# PYDANTIC MODELS REMOVED (v3.0 unified architecture)
# McpConfigRequest, McpConfigResponse, RegisterMcpRequest, RegisterMcpResponse
# These models were only used by auto-injection endpoints (now removed)


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


def validate_lan_config(lan_config: LANConfig) -> None:
    """
    Validate LAN configuration input.

    Args:
        lan_config: LAN configuration to validate

    Raises:
        HTTPException 400: If validation fails
    """
    import ipaddress

    # Validate username
    if len(lan_config.admin_username) < 3:
        raise HTTPException(status_code=400, detail="Admin username must be at least 3 characters long")

    if not lan_config.admin_username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400, detail="Admin username must contain only alphanumeric characters, hyphens, and underscores"
        )

    # Validate password
    if len(lan_config.admin_password) < 8:
        raise HTTPException(status_code=400, detail="Admin password must be at least 8 characters long")

    # Validate IP address
    try:
        ip = ipaddress.ip_address(lan_config.server_ip)

        # Reject link-local addresses (169.254.x.x)
        if ip.is_link_local:
            raise HTTPException(
                status_code=400,
                detail="Link-local IP addresses (169.254.x.x) are not allowed. Please use a valid LAN IP address.",
            )

        # Reject loopback addresses
        if ip.is_loopback:
            raise HTTPException(
                status_code=400,
                detail="Loopback addresses (127.x.x.x) are not allowed. Please use a valid LAN IP address.",
            )

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid IP address format: {lan_config.server_ip}")


def update_cors_origins_additive(config: dict[str, Any], server_ip: str = None, hostname: str = None) -> None:
    """
    Update CORS origins additively (preserves existing origins, adds new ones).

    v3.0 architecture: CORS management is additive to support both localhost
    and network access simultaneously.

    Args:
        config: Configuration dictionary to update
        server_ip: Server IP address for LAN/WAN mode (optional)
        hostname: Optional hostname for LAN/WAN access
    """
    # Get frontend port from config
    frontend_port = config.get("services", {}).get("dashboard", {}).get("port", 7274)

    # Ensure CORS config exists
    if "security" not in config:
        config["security"] = {}
    if "cors" not in config["security"]:
        config["security"]["cors"] = {}
    if "allowed_origins" not in config["security"]["cors"]:
        config["security"]["cors"]["allowed_origins"] = []

    # Get existing origins
    existing_origins = set(config["security"]["cors"]["allowed_origins"])

    # ALWAYS ensure base localhost origins are present
    localhost_origins = {
        f"http://127.0.0.1:{frontend_port}",
        f"http://localhost:{frontend_port}",
    }
    existing_origins.update(localhost_origins)

    # Add network origins if provided (additive)
    if server_ip:
        network_origin = f"http://{server_ip}:{frontend_port}"
        existing_origins.add(network_origin)
        logger.info(f"Added CORS origin for network access: {server_ip}")

    if hostname:
        hostname_origin = f"http://{hostname}:{frontend_port}"
        existing_origins.add(hostname_origin)
        logger.info(f"Added CORS origin for hostname access: {hostname}")

    # Update config with combined origins (sorted for consistency)
    config["security"]["cors"]["allowed_origins"] = sorted(list(existing_origins))
    logger.info(f"CORS origins updated (additive): {len(existing_origins)} total")


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(request: Request = None):
    """
    Get setup completion status.

    Returns the current state of the setup wizard, including:
    - Whether setup has been completed
    - Database configuration status (always true - configured by installer)
    - List of attached MCP tools
    - Current network deployment mode
    - Whether default password is still active (requires password change)

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

        # Get database initialization status from state manager
        database_initialized = state.get("database_initialized", False)

        # Get attached tools from state manager
        tools_attached = state.get("tools_enabled", [])

        # Check default password status from database
        # SECURITY: Default to True (force password change when uncertain)
        default_password_active = True
        try:
            # Get database session from request app state
            if request and hasattr(request.app, "state") and hasattr(request.app.state, "api_state"):
                db_manager = request.app.state.api_state.db_manager
                if db_manager:
                    from sqlalchemy import select
                    from src.giljo_mcp.models import SetupState as SetupStateModel

                    async with db_manager.get_session_async() as session:
                        stmt = select(SetupStateModel).where(SetupStateModel.tenant_key == tenant_key)
                        result = await session.execute(stmt)
                        setup_state_db = result.scalar_one_or_none()

                        if setup_state_db:
                            # Found setup_state - use its value
                            default_password_active = setup_state_db.default_password_active
                        else:
                            # No setup state in DB yet - assume default password active if admin user exists
                            from src.giljo_mcp.models import User
                            stmt_user = select(User).where(User.username == 'admin')
                            result_user = await session.execute(stmt_user)
                            admin_user = result_user.scalar_one_or_none()
                            # If admin user exists, password change required; if not, also require it (pristine DB)
                            default_password_active = True  # Always True until password is changed
        except Exception as e:
            logger.warning(f"Failed to check default password status: {e}")
            # SECURITY: Default to True (force password change on error - fail-safe)
            default_password_active = True

        return SetupStatusResponse(
            database_initialized=database_initialized,
            database_configured=database_configured,
            tools_attached=tools_attached,
            network_mode=network_mode,
            default_password_active=default_password_active,
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

    For LAN/WAN mode, this endpoint:
    - Validates input (username, password, IP address)
    - Creates admin User in database with hashed password
    - Generates API key for admin user
    - Updates CORS origins for network access
    - Configures API to bind to selected adapter IP

    For localhost mode:
    - No user creation
    - No API key generation
    - Binds to 127.0.0.1

    The endpoint is idempotent - calling it multiple times will update configuration.

    Args:
        request_body: Setup completion request with tools and network configuration
        request: FastAPI Request object (to access app state)

    Returns:
        Success response with confirmation message and API key (for LAN/WAN mode only)

    Raises:
        HTTPException 400: Invalid input (weak password, invalid IP, missing config)
        HTTPException 500: Database error, config write error
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
        config["setup"]["database_initialized"] = True
        config["setup"]["tools_attached"] = request_body.tools_attached
        config["setup"]["database_initialized_at"] = datetime.now(timezone.utc).isoformat()

        # Save deployment_context as metadata (top-level for easy access)
        config["deployment_context"] = request_body.deployment_context.value

        # Also save in installation section for backward compatibility
        if "installation" not in config:
            config["installation"] = {}

        config["installation"]["mode"] = request_body.deployment_context.value

        # Initialize response variables
        api_key = None
        admin_username = None
        requires_restart = False
        server_url = None

        # ========================================================================
        # v3.0 UNIFIED CONFIGURATION - NO MODE-DRIVEN BRANCHING
        # ========================================================================
        # In v3.0, ALL deployments use the same core configuration:
        # - API binds to 0.0.0.0 (firewall controls access)
        # - Authentication ALWAYS enabled
        # - Auto-login ALWAYS enabled for localhost clients
        # - Admin user created ONLY when lan_config provided
        # - CORS origins managed additively
        # - DeploymentContext saved as metadata only
        # ========================================================================

        # 1. ALWAYS set network binding to 0.0.0.0 (v3.0 unified architecture)
        if "services" not in config:
            config["services"] = {}
        if "api" not in config["services"]:
            config["services"]["api"] = {}
        if "dashboard" not in config["services"]:
            config["services"]["dashboard"] = {}

        config["services"]["api"]["host"] = "0.0.0.0"
        config["services"]["dashboard"]["host"] = "0.0.0.0"
        logger.info("v3.0: API and dashboard bound to 0.0.0.0 (firewall controls access)")

        # 2. ALWAYS enable authentication with auto-login for localhost
        if "features" not in config:
            config["features"] = {}

        config["features"]["authentication"] = True
        config["features"]["auto_login_localhost"] = True
        logger.info("v3.0: Authentication enabled with auto-login for localhost clients")

        # 3. OPTIONAL: Create admin user if lan_config provided
        if request_body.lan_config:
            logger.info("Creating admin user with lan_config credentials...")

            # Validate LAN configuration
            validate_lan_config(request_body.lan_config)

            # Create or update admin user in database
            try:
                from passlib.hash import bcrypt
                from sqlalchemy import select
                from src.giljo_mcp.models import User

                # Get database session from request app state
                if not (request and hasattr(request.app, "state") and hasattr(request.app.state, "api_state")):
                    raise HTTPException(
                        status_code=500,
                        detail="Database connection not available. Please restart the API server and try again.",
                    )

                db_manager = request.app.state.api_state.db_manager
                if not db_manager:
                    raise HTTPException(
                        status_code=500,
                        detail="Database manager not initialized. Please restart the API server and try again.",
                    )

                async with db_manager.get_session_async() as session:
                    # Check if user already exists
                    stmt = select(User).where(User.username == request_body.lan_config.admin_username)
                    result = await session.execute(stmt)
                    existing_user = result.scalar_one_or_none()

                    if existing_user:
                        # Update existing user's password (idempotent behavior)
                        existing_user.password_hash = bcrypt.hash(request_body.lan_config.admin_password)
                        existing_user.is_active = True
                        existing_user.role = "admin"
                        await session.flush()
                        admin_username = existing_user.username
                        logger.info(f"Updated existing admin user in database: {admin_username}")
                    else:
                        # Create new admin user
                        new_user = User(
                            username=request_body.lan_config.admin_username,
                            email=None,  # Email not collected in setup wizard yet
                            password_hash=bcrypt.hash(request_body.lan_config.admin_password),
                            role="admin",
                            tenant_key=tenant_key,
                            is_active=True,
                            created_at=datetime.now(timezone.utc),
                        )
                        session.add(new_user)
                        await session.flush()
                        admin_username = new_user.username
                        logger.info(f"Created admin user in database: {admin_username}")

                    # Commit user creation
                    await session.commit()

                logger.info("Admin user configured successfully (JWT auth enabled)")

            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(f"Failed to configure admin user: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to configure authentication: {str(e)}")

            # Update CORS origins additively (ADD network origins)
            update_cors_origins_additive(
                config,
                server_ip=request_body.lan_config.server_ip,
                hostname=request_body.lan_config.hostname,
            )

            # Save LAN server metadata (informational only)
            if "server" not in config:
                config["server"] = {}

            config["server"]["ip"] = request_body.lan_config.server_ip
            config["server"]["hostname"] = request_body.lan_config.hostname
            config["server"]["admin_user"] = request_body.lan_config.admin_username
            config["server"]["firewall_configured"] = request_body.lan_config.firewall_configured

            # Save selected adapter information if provided
            if request_body.lan_config.adapter_name and request_body.lan_config.adapter_id:
                config["server"]["selected_adapter"] = {
                    "name": request_body.lan_config.adapter_name,
                    "id": request_body.lan_config.adapter_id,
                    "initial_ip": request_body.lan_config.server_ip,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
                logger.info(
                    f"Saved adapter info: {request_body.lan_config.adapter_name} "
                    f"({request_body.lan_config.server_ip})"
                )

            # Enable API keys for network access (optional feature)
            config["features"]["api_keys_enabled"] = True
            logger.info("API keys enabled for network access")

        else:
            # No lan_config - localhost-only metadata
            logger.info("No lan_config provided - localhost-only deployment")

            # Remove server section if switching from LAN to localhost
            if "server" in config:
                del config["server"]
                logger.info("Removed server metadata (switched to localhost-only)")

            # Ensure base localhost CORS origins are present
            update_cors_origins_additive(config)

            # API keys optional for localhost-only
            config["features"]["api_keys_enabled"] = False

        # 4. Build server URL for response
        api_port = config.get("services", {}).get("api", {}).get("port", 7272)
        if request_body.lan_config:
            server_url = f"http://{request_body.lan_config.server_ip}:{api_port}"
        else:
            server_url = f"http://127.0.0.1:{api_port}"

        # 5. No restart required in v3.0 (already bound to 0.0.0.0)
        requires_restart = False
        logger.info("v3.0: No restart required (already bound to 0.0.0.0)")

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
                "api_keys_configured": request_body.deployment_context == DeploymentContext.LAN,
                "cors_configured": request_body.deployment_context == DeploymentContext.LAN,
                "serena_enabled": request_body.serena_enabled,
            }

            # Get version for tracking
            setup_version = config.get("installation", {}).get("version", "2.0.0")

            # Mark database as initialized with version tracking
            state_manager.mark_database_initialized(setup_version=setup_version, config_snapshot=config_snapshot)

            # Update additional state fields
            state_manager.update_state(
                tools_enabled=request_body.tools_attached,
                features_configured=features_configured,
                install_mode=request_body.deployment_context.value,
                validation_passed=True,
                validation_failures=[],
            )

            logger.info(f"✅ Setup state saved to SetupStateManager for tenant {tenant_key}")

        except Exception as e:
            # Non-fatal - log but don't fail the setup
            logger.warning(
                f"Failed to save setup state to SetupStateManager: {e}. "
                "Setup completed but state tracking may be incomplete."
            )

        logger.info(
            f"Setup completed successfully: mode={request_body.deployment_context.value}, "
            f"tools={len(request_body.tools_attached)}, serena={request_body.serena_enabled}"
        )

        # Build response message and response model
        if request_body.deployment_context in [DeploymentContext.LAN, DeploymentContext.WAN]:
            message = f"{request_body.deployment_context.value.upper()} setup completed successfully. Use your admin credentials to login."
        else:
            message = "Setup completed successfully. Configuration has been saved."

        # Build response with updated model fields
        response_data = {
            "success": True,
            "message": message,
            "api_key": None,  # No API key for dashboard login - JWT auth only
            "requires_restart": requires_restart,
            "mode": request_body.deployment_context.value,
            "server_url": server_url,
            "admin_username": admin_username,
        }

        return SetupCompleteResponse(**response_data)

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
            tenant_key=tenant_key, current_version=current_setup_version, required_db_version=current_db_version
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
        logger.info(f"Migrating setup state to version {current_setup_version} " f"for tenant {tenant_key}")

        state_manager.migrate_state(new_setup_version=current_setup_version, new_database_version=current_db_version)

        # Validate state after migration
        valid, failures = state_manager.validate_state()

        if not valid:
            logger.warning(f"Setup state validation failed after migration: {failures}")
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


# AUTO-INJECTION ENDPOINTS REMOVED (v3.0 unified architecture)
# Use downloadable setup scripts instead for all users (localhost and remote)


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


# /register-mcp endpoint REMOVED - auto-injection replaced with downloadable scripts


# ================================================================================
# LAN Mode Admin User Creation
# ================================================================================


class AdminUserRequest(BaseModel):
    """Request model for creating admin user"""

    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")
    email: str = Field(..., description="Admin email")


class AdminUserResponse(BaseModel):
    """Response model for admin user creation"""

    success: bool
    api_key: str = Field(..., description="Generated API key (shown once)")
    message: str


async def get_db_session():
    """Get async database session"""
    import os
    from src.giljo_mcp.database import DatabaseManager

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    async with db_manager.get_session_async() as session:
        yield session


@router.post("/admin-user", response_model=AdminUserResponse)
async def create_admin_user(request: AdminUserRequest = Body(...)):
    """
    Create admin user for LAN mode with API key generation.

    This endpoint is called during the setup wizard when LAN mode is selected.
    It creates an admin user in the database and generates an API key for authentication.

    The API key is returned in plaintext ONCE and must be saved by the user.
    """
    try:
        import os
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.giljo_mcp.database import DatabaseManager
        from src.giljo_mcp.models import User, APIKey
        from src.giljo_mcp.tenant import generate_tenant_key
        from src.giljo_mcp.api_key_utils import generate_api_key, hash_api_key, get_key_prefix
        import bcrypt
        from datetime import datetime, timezone

        # Get database session
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is required")

        db_manager = DatabaseManager(database_url=db_url, is_async=True)
        async with db_manager.get_session_async() as db:
            # Delete existing users with same username or email (wizard is destructive)
            from sqlalchemy import select, delete

            # Delete any existing API keys for users we're about to delete
            stmt = select(User.id).where((User.username == request.username) | (User.email == request.email))
            result = await db.execute(stmt)
            existing_user_ids = [row[0] for row in result.fetchall()]

            if existing_user_ids:
                logger.info(f"Wizard: Deleting {len(existing_user_ids)} existing user(s) and their API keys")
                # Delete API keys first (foreign key constraint)
                await db.execute(delete(APIKey).where(APIKey.user_id.in_(existing_user_ids)))
                # Delete users
                await db.execute(delete(User).where(User.id.in_(existing_user_ids)))
                await db.flush()

            # Hash password
            password_hash = bcrypt.hashpw(request.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            # Create admin user
            tenant_key = generate_tenant_key(project_name=f"admin_{request.username}")
            admin_user = User(
                username=request.username,
                email=request.email,
                password_hash=password_hash,
                role="admin",
                tenant_key=tenant_key,
            )

            db.add(admin_user)
            await db.flush()  # Get user ID

            # Generate API key
            plaintext_key = generate_api_key()
            hashed_key = hash_api_key(plaintext_key)
            key_prefix = get_key_prefix(plaintext_key, length=12)

            # Create API key record
            api_key = APIKey(
                user_id=admin_user.id,
                key_hash=hashed_key,
                key_prefix=key_prefix,
                name=f"Admin Setup Key - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                permissions=["*"],  # Grant full admin access
                tenant_key=tenant_key,
            )

            db.add(api_key)
            await db.commit()

            logger.info(f"Admin user '{request.username}' created with API key")

            return AdminUserResponse(
                success=True, api_key=plaintext_key, message=f"Admin user '{request.username}' created successfully"
            )

    except Exception as e:
        logger.error(f"Error creating admin user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create admin user: {e}")

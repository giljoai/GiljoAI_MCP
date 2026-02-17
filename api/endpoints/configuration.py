"""
Configuration management API endpoints
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


# Pydantic models for request/response
class ConfigurationGet(BaseModel):
    key: str = Field(..., description="Configuration key path (e.g., 'database.pool_size')")
    default: Optional[Any] = Field(None, description="Default value if key not found")


class ConfigurationSet(BaseModel):
    key: str = Field(..., description="Configuration key path")
    value: Any = Field(..., description="Configuration value")
    tenant_key: Optional[str] = Field(None, description="Tenant-specific configuration")


class ConfigurationUpdate(BaseModel):
    configurations: dict[str, Any] = Field(..., description="Multiple configuration updates")
    tenant_key: Optional[str] = Field(None, description="Tenant-specific configuration")


class ConfigurationResponse(BaseModel):
    key: str
    value: Any
    source: str = Field(..., description="Configuration source (default, file, env, database)")
    tenant_key: Optional[str] = None
    updated_at: datetime


class SystemConfigResponse(BaseModel):
    database: dict[str, Any]
    api: dict[str, Any]
    orchestration: dict[str, Any]
    security: dict[str, Any]
    features: dict[str, Any]


@router.get("/")
async def get_system_configuration():
    """
    Get complete system configuration from config.yaml.

    Returns the full config.yaml structure that the frontend expects,
    including installation.mode, services, security, database, etc.

    Sensitive data (passwords, API keys) are masked for security.
    """
    from src.giljo_mcp._config_io import read_config

    config = read_config()

    if not config:
        raise HTTPException(status_code=500, detail="config.yaml is empty or not found")

    # Mask sensitive data for security
    if "database" in config and "password" in config.get("database", {}):
        # Mask database password
        config["database"]["password"] = "****" if config["database"]["password"] else ""

    if "security" in config and "api_keys" in config.get("security", {}):
        # Mask API keys
        api_keys = config["security"].get("api_keys", {})
        if isinstance(api_keys, dict):
            for key in api_keys:
                if isinstance(api_keys[key], str):
                    api_keys[key] = "****"

    # Return the full structure (matches config.yaml format)
    return config


@router.get("/key/{key_path}", response_model=ConfigurationResponse)
async def get_configuration(key_path: str, default: Optional[Any] = None):
    """Get specific configuration value by key path"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Replace URL path separator with dot notation
    key = key_path.replace("/", ".")
    value = state.config.get(key, default)

    if value is None and default is None:
        raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")

    # Determine source
    source = "default"
    if hasattr(state.config, "_sources") and key in state.config._sources:
        source = state.config._sources[key]

    return ConfigurationResponse(key=key, value=value, source=source, updated_at=datetime.now(timezone.utc))


@router.put("/key/{key_path}")
async def set_configuration(key_path: str, config: ConfigurationSet):
    """Set configuration value (runtime only, not persisted)"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Replace URL path separator with dot notation
    key = key_path.replace("/", ".")

    # Validate key format
    if not key or ".." in key:
        raise HTTPException(status_code=400, detail="Invalid configuration key")

    # Set configuration value
    state.config.set(key, config.value)

    return {
        "success": True,
        "key": key,
        "value": config.value,
        "message": "Configuration updated (runtime only)",
    }


@router.patch("/")
async def update_configurations(update: ConfigurationUpdate):
    """Update multiple configuration values at once"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    updated = []
    failed = []

    for key, value in update.configurations.items():
        try:
            state.config.set(key, value)
            updated.append(key)
        except Exception as e:  # noqa: BLE001, PERF203 - Partial update resilience: collect failures, continue loop
            failed.append({"key": key, "error": str(e)})

    return {
        "success": len(failed) == 0,
        "updated": updated,
        "failed": failed,
        "message": f"Updated {len(updated)} configurations",
    }


@router.post("/reload")
async def reload_configuration():
    """Reload configuration from files and environment"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Reload configuration
    state.config.reload()

    return {"success": True, "message": "Configuration reloaded successfully"}


@router.get("/tenants", response_model=list[str])
async def list_tenant_configurations():
    """List all tenants with custom configurations"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as session:
        from src.giljo_mcp.repositories import ConfigurationRepository

        repo = ConfigurationRepository(state.db_manager)
        tenants = await repo.list_tenant_keys(session)

        return tenants


@router.get("/tenant/{tenant_key}", response_model=dict[str, Any])
async def get_tenant_configuration(tenant_key: str):
    """Get tenant-specific configuration"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as session:
        from src.giljo_mcp.repositories import ConfigurationRepository

        repo = ConfigurationRepository(state.db_manager)
        configs = await repo.get_tenant_configurations(session, tenant_key)

        if not configs:
            raise HTTPException(status_code=404, detail=f"No configuration found for tenant '{tenant_key}'")

        tenant_config = {}
        for config in configs:
            tenant_config[config.key] = json.loads(config.value) if config.value else None

        return tenant_config


@router.put("/tenant/{tenant_key}")
async def set_tenant_configuration(
    tenant_key: str,
    configurations: dict[str, Any] = Body(..., description="Tenant-specific configurations"),
):
    """Set tenant-specific configuration"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as session:
        from src.giljo_mcp.models import Configuration
        from src.giljo_mcp.repositories import ConfigurationRepository

        repo = ConfigurationRepository(state.db_manager)

        for key, value in configurations.items():
            config = await repo.get_configuration_by_key(session, tenant_key, key)

            if config:
                config.value = json.dumps(value) if value is not None else None
                config.updated_at = datetime.now(timezone.utc)
            else:
                config = Configuration(
                    tenant_key=tenant_key, key=key, value=json.dumps(value) if value is not None else None
                )
                session.add(config)

        await session.commit()

        return {
            "success": True,
            "tenant_key": tenant_key,
            "configurations_updated": len(configurations),
            "message": f"Tenant configuration updated for '{tenant_key}'",
        }


@router.delete("/tenant/{tenant_key}")
async def delete_tenant_configuration(tenant_key: str):
    """Delete all tenant-specific configurations"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as session:
        from src.giljo_mcp.repositories import ConfigurationRepository

        repo = ConfigurationRepository(state.db_manager)
        deleted_count = await repo.delete_tenant_configurations(session, tenant_key)

        await session.commit()

        if deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"No configuration found for tenant '{tenant_key}'")

        return {
            "success": True,
            "tenant_key": tenant_key,
            "configurations_deleted": deleted_count,
            "message": f"Deleted {deleted_count} configurations for tenant '{tenant_key}'",
        }


# Database-specific endpoints


class DatabaseConfigResponse(BaseModel):
    host: str
    port: int
    name: str
    user: str
    password_masked: str


class DatabasePasswordUpdate(BaseModel):
    password: str = Field(
        ...,
        description="New database password (min 8 chars, must contain uppercase, lowercase, number, and special char)",
        min_length=8,
    )


@router.get("/database", response_model=DatabaseConfigResponse)
async def get_database_configuration():
    """Get database configuration (password masked) - reads from .env file"""
    # Read directly from .env file
    from dotenv import dotenv_values

    env_path = Path.cwd() / ".env"

    if not env_path.exists():
        raise HTTPException(status_code=404, detail=".env file not found")

    env_vars = dotenv_values(env_path)

    # Get database config (these should match what installer created)
    host = env_vars.get("DB_HOST", "localhost")
    port = int(env_vars.get("DB_PORT", "5432"))
    name = env_vars.get("DB_NAME", "giljo_mcp")
    user = env_vars.get("DB_USER", "giljo_user")
    password = env_vars.get("DB_PASSWORD", "")

    # Mask password (show actual length for reference)
    password_masked = "*" * len(password) if password else "****"

    return DatabaseConfigResponse(host=host, port=port, name=name, user=user, password_masked=password_masked)


@router.post("/database/password")
async def update_database_password(update: DatabasePasswordUpdate):
    """
    Update database password for giljo_user in both PostgreSQL and .env file

    Password Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character (@$!%*?&)
    """
    import re

    from dotenv import dotenv_values, set_key
    from sqlalchemy import create_engine, text

    env_path = Path.cwd() / ".env"

    # Ensure .env exists
    if not env_path.exists():
        raise HTTPException(status_code=404, detail=".env file not found")

    # Validate password strength (Pydantic already does this, but double-check)
    if len(update.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", update.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", update.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")

    if not re.search(r"\d", update.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")

    if not re.search(r"[@$!%*?&]", update.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character (@$!%*?&)")

    # Read current database configuration
    env_vars = dotenv_values(env_path)
    db_user = env_vars.get("DB_USER", "giljo_user")
    db_host = env_vars.get("DB_HOST", "localhost")
    db_port = env_vars.get("DB_PORT", "5432")
    db_name = env_vars.get("DB_NAME", "giljo_mcp")
    current_password = env_vars.get("DB_PASSWORD", "")

    if not current_password:
        raise HTTPException(status_code=400, detail="Current password not found in .env file")

    # Step 1: Update PostgreSQL password using current credentials
    try:
        # Connect with current password
        current_db_url = f"postgresql://{db_user}:{current_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(current_db_url)

        with engine.connect() as conn:
            # Execute ALTER USER with new password
            # Use parameterized query to prevent SQL injection
            conn.execute(text(f"ALTER USER {db_user} WITH PASSWORD :new_password"), {"new_password": update.password})
            conn.commit()

        engine.dispose()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update PostgreSQL password: {e!s}. Please verify current password is correct.",
        ) from e

    # Step 2: Update .env file with new password
    try:
        set_key(env_path, "DB_PASSWORD", update.password)

        # Also update DATABASE_URL with new password
        new_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
        set_key(env_path, "DATABASE_URL", new_db_url)

    except Exception as e:
        # If .env update fails, we need to rollback PostgreSQL password
        try:
            rollback_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
            rollback_engine = create_engine(rollback_db_url)
            with rollback_engine.connect() as conn:
                conn.execute(
                    text(f"ALTER USER {db_user} WITH PASSWORD :old_password"), {"old_password": current_password}
                )
                conn.commit()
            rollback_engine.dispose()
        except (OSError, ValueError):
            pass  # Best effort rollback  # nosec B110

        raise HTTPException(
            status_code=500, detail=f"Failed to update .env file: {e!s}. PostgreSQL password has been rolled back."
        ) from e

    # Step 3: Test new connection
    try:
        test_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
        test_engine = create_engine(test_db_url)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Password updated but connection test failed: {e!s}. Application restart required.",
        ) from e

    return {
        "success": True,
        "message": "Database password updated successfully in both PostgreSQL and .env file. Application restart required for changes to take effect.",
        "details": {"postgresql_updated": True, "env_file_updated": True, "connection_tested": True},
    }


@router.get("/frontend")
async def get_frontend_configuration():
    """
    Get frontend-specific configuration.

    v3.0 Unified Architecture:
    Returns essential configuration for frontend to connect to the API server.
    Does NOT include deployment mode (removed in v3.0 - unified architecture only).

    Returns:
        - api.host: The host where the API is accessible (e.g., "192.168.1.100" or "localhost")
        - api.port: The API port (e.g., 7272)
        - websocket.url: The full WebSocket URL (e.g., "ws://192.168.1.100:7272")
        - security.api_keys_required: Whether API keys are required

    This endpoint does NOT expose sensitive data like passwords or API keys.

    Note:
        v3.0 removes the 'mode' field from response. Server always binds to 0.0.0.0,
        and the frontend connects via the configured external_host (set during installation).
        OS firewall controls network access (defense in depth).
    """
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Extract frontend-needed configuration via ConfigManager
    api_port = state.config.get_nested("services.api.port", 7272)
    api_keys_required = state.config.get_nested("features.api_keys_required", default=False)
    frontend_host = state.config.get_nested("services.external_host", "localhost")
    ssl_enabled = state.config.get_nested("features.ssl_enabled", default=False)

    # Build WebSocket URL (use ws:// for http, wss:// for https)
    ws_protocol = "wss" if ssl_enabled else "ws"
    ws_url = f"{ws_protocol}://{frontend_host}:{api_port}"

    # v3.0 Unified Architecture: No 'mode' field in response
    return {
        "api": {
            "host": frontend_host,  # Frontend connection host (external_host from config)
            "port": api_port,
        },
        "websocket": {
            "url": ws_url,
        },
        "security": {
            "api_keys_required": api_keys_required,
        },
    }


@router.get("/health/database")
async def test_database_connection():
    """Test database connection"""
    from api.app import state

    if not state.db_manager:
        return {"success": False, "error": "Database manager not initialized"}

    try:
        async with state.db_manager.get_session_async() as session:
            from src.giljo_mcp.repositories import ConfigurationRepository

            repo = ConfigurationRepository(state.db_manager)
            is_healthy = await repo.execute_health_check(session)

            if is_healthy:
                return {"success": True, "message": "Database connection successful"}
            return {"success": False, "error": "Database health check returned False"}

    except (RuntimeError, OSError, ValueError) as e:
        return {"success": False, "error": f"Database connection failed: {e!s}"}

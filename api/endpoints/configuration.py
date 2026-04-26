# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Configuration management API endpoints
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin, require_ce_mode
from giljo_mcp.models import User
from giljo_mcp.services.settings_service import SettingsService


logger = logging.getLogger(__name__)

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


class SuccessResponse(BaseModel):
    """Generic success response for operations that return a simple status message."""

    success: bool = True
    message: str


class SystemConfigResponse(BaseModel):
    database: dict[str, Any]
    api: dict[str, Any]
    orchestration: dict[str, Any]
    security: dict[str, Any]
    features: dict[str, Any]


@router.get("/")
async def get_system_configuration(current_user: User = Depends(get_current_active_user)):
    """
    Get complete system configuration from config.yaml.

    Returns the full config.yaml structure that the frontend expects,
    including installation.mode, services, security, database, etc.

    Sensitive data (passwords, API keys) are masked for security.
    """
    from giljo_mcp._config_io import read_config

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
async def get_configuration(
    key_path: str,
    default: Optional[Any] = None,
    current_user: User = Depends(get_current_active_user),
    _ce: None = Depends(require_ce_mode),
):
    """Get specific configuration value by key path"""
    from api.app_state import state

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


# SERVER-LEVEL: mutates in-memory config.yaml (state.config.set), CE-only
@router.put("/key/{key_path}")
async def set_configuration(
    key_path: str,
    config: ConfigurationSet,
    current_user: User = Depends(require_admin),
    _ce: None = Depends(require_ce_mode),
):
    """Set configuration value (runtime only, not persisted)"""
    from api.app_state import state

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


# SERVER-LEVEL: bulk mutates in-memory config.yaml (state.config.set), CE-only
@router.patch("/")
async def update_configurations(
    update: ConfigurationUpdate,
    current_user: User = Depends(require_admin),
    _ce: None = Depends(require_ce_mode),
):
    """Update multiple configuration values at once"""
    from api.app_state import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    updated = []
    failed = []

    for key, value in update.configurations.items():
        try:
            state.config.set(key, value)
            updated.append(key)
        except Exception as e:  # noqa: BLE001, PERF203 - Partial update resilience: collect failures, continue loop
            # Log full detail server-side; return a generic message to avoid
            # leaking internal exception text to the caller (CodeQL: py/stack-trace-exposure)
            logger.warning("Configuration update failed for key %r: %s", key, e)
            failed.append({"key": key, "error": "Failed to update configuration key"})

    return {
        "success": len(failed) == 0,
        "updated": updated,
        "failed": failed,
        "message": f"Updated {len(updated)} configurations",
    }


# SERVER-LEVEL: reloads config.yaml from disk (state.config.reload), CE-only
@router.post("/reload")
async def reload_configuration(
    current_user: User = Depends(require_admin),
    _ce: None = Depends(require_ce_mode),
):
    """Reload configuration from files and environment"""
    from api.app_state import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Reload configuration
    state.config.reload()

    return SuccessResponse(message="Configuration reloaded successfully")


# TENANT-LEVEL
@router.get("/tenant", response_model=dict[str, Any])
async def get_tenant_configuration(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get configuration for the authenticated user's tenant"""
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=401, detail="Tenant key not available from authentication")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    from giljo_mcp.services.tenant_configuration_service import TenantConfigurationService

    config_service = TenantConfigurationService(
        db_manager=state.db_manager,
        tenant_key=tenant_key,
    )
    configs = await config_service.get_tenant_configurations()

    if not configs:
        raise HTTPException(status_code=404, detail="No configuration found for your tenant")

    tenant_config = {}
    for config in configs:
        tenant_config[config.key] = json.loads(config.value) if config.value else None

    return tenant_config


# TENANT-LEVEL
@router.put("/tenant")
async def set_tenant_configuration(
    request: Request,
    configurations: dict[str, Any] = Body(..., description="Tenant-specific configurations"),
    current_user: User = Depends(require_admin),
):
    """Set configuration for the authenticated user's tenant.

    Sprint 003c: Write routed through TenantConfigurationService.
    """
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=401, detail="Tenant key not available from authentication")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    from giljo_mcp.services.tenant_configuration_service import TenantConfigurationService

    service = TenantConfigurationService(db_manager=state.db_manager, tenant_key=tenant_key)
    count = await service.set_configurations(configurations)

    return {
        "success": True,
        "configurations_updated": count,
        "message": "Tenant configuration updated",
    }


# TENANT-LEVEL
@router.delete("/tenant")
async def delete_tenant_configuration(request: Request, current_user: User = Depends(require_admin)):
    """Delete all configurations for the authenticated user's tenant.

    Sprint 003c: Write routed through TenantConfigurationService.
    """
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=401, detail="Tenant key not available from authentication")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    from giljo_mcp.services.tenant_configuration_service import TenantConfigurationService

    service = TenantConfigurationService(db_manager=state.db_manager, tenant_key=tenant_key)
    deleted_count = await service.delete_all_configurations()

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No configuration found for your tenant")

    return {
        "success": True,
        "configurations_deleted": deleted_count,
        "message": f"Deleted {deleted_count} configurations",
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


# SERVER-LEVEL: reads .env file (DB_HOST, DB_PORT, DB_PASSWORD), CE-only
@router.get("/database", response_model=DatabaseConfigResponse)
async def get_database_configuration(
    current_user: User = Depends(require_admin),
    _ce: None = Depends(require_ce_mode),
):
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


# SERVER-LEVEL: ALTER USER on PostgreSQL + writes .env DB_PASSWORD, CE-only
@router.post("/database/password")
async def update_database_password(
    update: DatabasePasswordUpdate,
    current_user: User = Depends(require_admin),
    _ce: None = Depends(require_ce_mode),
):
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
            # Use psycopg2.sql.Identifier for safe identifier quoting (prevents SQL injection via db_user)
            from psycopg2 import sql as psycopg2_sql

            safe_stmt = psycopg2_sql.SQL("ALTER USER {} WITH PASSWORD %(new_password)s").format(
                psycopg2_sql.Identifier(db_user)
            )
            raw_conn = conn.connection.dbapi_connection
            with raw_conn.cursor() as cur:
                cur.execute(safe_stmt, {"new_password": update.password})
            conn.commit()

        engine.dispose()

    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        logger.error("Failed to update PostgreSQL password: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to update PostgreSQL password. Please verify current password is correct.",
        ) from e

    # Step 2: Update .env file with new password
    try:
        set_key(env_path, "DB_PASSWORD", update.password)

        # Also update DATABASE_URL with new password
        new_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
        set_key(env_path, "DATABASE_URL", new_db_url)

    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        # If .env update fails, we need to rollback PostgreSQL password
        try:
            rollback_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
            rollback_engine = create_engine(rollback_db_url)
            with rollback_engine.connect() as conn:
                from psycopg2 import sql as psycopg2_sql

                safe_stmt = psycopg2_sql.SQL("ALTER USER {} WITH PASSWORD %(old_password)s").format(
                    psycopg2_sql.Identifier(db_user)
                )
                raw_conn = conn.connection.dbapi_connection
                with raw_conn.cursor() as cur:
                    cur.execute(safe_stmt, {"old_password": current_password})
                conn.commit()
            rollback_engine.dispose()
        except (OSError, ValueError):
            pass  # Best effort rollback  # nosec B110

        raise HTTPException(
            status_code=500, detail="Failed to update .env file. PostgreSQL password has been rolled back."
        ) from e

    # Step 3: Test new connection
    try:
        test_db_url = f"postgresql://{db_user}:{update.password}@{db_host}:{db_port}/{db_name}"
        test_engine = create_engine(test_db_url)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()

    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        raise HTTPException(
            status_code=500,
            detail="Password updated but connection test failed. Application restart required.",
        ) from e

    return {
        "success": True,
        "message": "Database password updated successfully in both PostgreSQL and .env file. Application restart required for changes to take effect.",
        "details": {"postgresql_updated": True, "env_file_updated": True, "connection_tested": True},
    }


class SSLToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable SSL")
    domain: str = Field("localhost", description="Domain name for certificate generation")


class SSLStatusResponse(BaseModel):
    ssl_enabled: bool
    has_certificate: bool
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    restart_required: bool = True
    message: str


# SERVER-LEVEL: reads SSL paths from settings (server-global cert/key files), CE-only
@router.get("/ssl", response_model=SSLStatusResponse)
async def get_ssl_status(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _ce: None = Depends(require_ce_mode),
):
    """Get current SSL/HTTPS configuration status from database."""
    service = SettingsService(db, current_user.tenant_key)
    security = await service.get_settings("security")

    ssl_enabled = security.get("ssl_enabled", False)
    cert_path = security.get("ssl_cert_path")
    key_path = security.get("ssl_key_path")

    has_cert = bool(cert_path and key_path and Path(cert_path).exists() and Path(key_path).exists())

    return SSLStatusResponse(
        ssl_enabled=ssl_enabled,
        has_certificate=has_cert,
        cert_path=cert_path if has_cert else None,
        key_path=key_path if has_cert else None,
        restart_required=False,
        message="HTTPS is enabled" if ssl_enabled else "HTTPS is disabled",
    )


# SERVER-LEVEL: generates server-global SSL certs + writes config.yaml, CE-only
@router.post("/ssl", response_model=SSLStatusResponse)
async def toggle_ssl(
    request_body: SSLToggleRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    _ce: None = Depends(require_ce_mode),
):
    """Enable or disable SSL/HTTPS. Generates self-signed certificates if none exist."""
    from giljo_mcp._config_io import read_config, write_config

    service = SettingsService(db, current_user.tenant_key)
    security = await service.get_settings("security")

    cert_path = security.get("ssl_cert_path")
    key_path = security.get("ssl_key_path")
    has_cert = bool(cert_path and key_path and Path(cert_path).exists() and Path(key_path).exists())

    # Fallback: check config.yaml paths if DB doesn't have them yet
    if not has_cert:
        config = read_config()
        cert_path = config.get("paths", {}).get("ssl_cert")
        key_path = config.get("paths", {}).get("ssl_key")
        has_cert = bool(cert_path and key_path and Path(cert_path).exists() and Path(key_path).exists())

    if request_body.enabled and not has_cert:
        # Generate self-signed certificates
        certs_dir = Path.cwd() / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)

        generated_key = certs_dir / "ssl_key.pem"
        generated_cert = certs_dir / "ssl_cert.pem"

        import re
        import subprocess

        # Validate domain against allowlist of safe hostname characters before
        # interpolating into the openssl -subj argument (CodeQL: py/command-line-injection)
        domain = request_body.domain or ""
        if not re.fullmatch(r"[A-Za-z0-9.\-]{1,253}", domain):
            raise HTTPException(
                status_code=400,
                detail="Invalid domain: must contain only letters, digits, hyphens, and dots.",
            )

        cmd = [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-keyout",
            str(generated_key),
            "-out",
            str(generated_cert),
            "-days",
            "365",
            "-nodes",
            "-subj",
            f"/CN={domain}/O=GiljoAI MCP/C=US",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=500,
                detail="OpenSSL not found. Install OpenSSL to generate certificates.",
            ) from e
        except subprocess.CalledProcessError as e:
            raise HTTPException(
                status_code=500,
                detail="Certificate generation failed. Check server logs for details.",
            ) from e

        cert_path = str(generated_cert.absolute())
        key_path = str(generated_key.absolute())
        has_cert = True

    # Write to database (source of truth for runtime)
    security["ssl_enabled"] = request_body.enabled
    if cert_path:
        security["ssl_cert_path"] = cert_path
    if key_path:
        security["ssl_key_path"] = key_path
    await service.update_settings("security", security)

    # Also write to config.yaml for startup bootstrap (needed before DB is available)
    config = read_config()
    if "features" not in config:
        config["features"] = {}
    config["features"]["ssl_enabled"] = request_body.enabled
    if cert_path and key_path:
        if "paths" not in config:
            config["paths"] = {}
        config["paths"]["ssl_cert"] = cert_path
        config["paths"]["ssl_key"] = key_path
    write_config(config)

    ssl_status = "enabled" if request_body.enabled else "disabled"
    return SSLStatusResponse(
        ssl_enabled=request_body.enabled,
        has_certificate=has_cert,
        cert_path=cert_path if has_cert else None,
        key_path=key_path if has_cert else None,
        restart_required=True,
        message=f"HTTPS {ssl_status}. Server restart required for changes to take effect.",
    )


@router.get("/frontend")
async def get_frontend_configuration(request: Request):
    """Get frontend-specific configuration (host, port, websocket URL, security flags).

    Response shape (INF-5012b): api.host/port/protocol derive from
    request.base_url (honors X-Forwarded-* via uvicorn proxy_headers), matching
    the pattern websocket.url already uses. api.port is int | null — null when
    implicit on a reverse proxy (standard 443/80), otherwise numeric (e.g. 7272
    for CE localhost). Frontend must branch on null to omit the ":port" segment.
    """
    from urllib.parse import urlparse

    from api.app_state import GILJO_MODE, state
    from giljo_mcp import __version__ as giljo_version

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    # Extract non-URL frontend configuration via ConfigManager
    api_keys_required = state.config.get_nested("features.api_keys_required", default=False)
    ssl_enabled = state.config.get_nested("features.ssl_enabled", default=False)

    # Derive api.host/port/protocol from the request's public base URL (INF-5012b).
    # Honors X-Forwarded-Host / X-Forwarded-Proto via uvicorn proxy_headers so
    # Cloudflare Tunnel, customer nginx, and mkcert LAN deployments all emit
    # the user-facing URL rather than the server's bind address.
    base = str(request.base_url).rstrip("/")
    parsed = urlparse(base)
    api_host = parsed.hostname or "localhost"
    api_port = parsed.port  # None when implicit (standard 443/80 through proxy)
    api_protocol = parsed.scheme or ("https" if ssl_enabled else "http")

    ws_url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    ws_protocol = "wss" if ws_url.startswith("wss://") else "ws"

    default_tenant_key = state.config.tenant.default_tenant_key or ""

    # Detect remote client: compare request IP against local addresses and server's own host
    is_remote_client = _is_remote_client(request, api_host)

    return {
        "api": {
            "host": api_host,  # Public host derived from request.base_url
            "port": api_port,  # None when implicit (standard 443/80)
            "protocol": api_protocol,
            "ssl_enabled": ssl_enabled,
            "is_remote_client": is_remote_client,
        },
        "websocket": {
            "url": ws_url,
            "protocol": ws_protocol,
        },
        "security": {
            "api_keys_required": api_keys_required,
            "default_tenant_key": default_tenant_key,
        },
        "edition": {"ce": "community", "demo": "demo", "saas": "saas"}.get(GILJO_MODE, "community"),
        "giljo_mode": GILJO_MODE,
        "version": giljo_version,
    }


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


def _is_remote_client(request: Request, server_host: str) -> bool:
    """Check if the requesting client is on a different machine than the server.

    Returns False for localhost, loopback, and the server's own external_host IP.
    Returns True for any other client IP (i.e., a remote machine on the LAN).
    """
    client_ip = _get_client_ip(request)
    local_addresses = {"127.0.0.1", "::1", "localhost", server_host}
    return client_ip not in local_addresses


@router.get(
    "/root-ca",
    dependencies=[Depends(get_current_active_user)],
)
async def download_root_ca():
    """Download the mkcert root CA certificate for trusting on remote machines.

    Only available when HTTPS is enabled and mkcert root CA exists.
    Requires authentication.
    """
    import subprocess

    from api.app_state import state

    ssl_enabled = state.config.get_nested("features.ssl_enabled", default=False) if state.config else False
    if not ssl_enabled:
        raise HTTPException(status_code=404, detail="HTTPS is not enabled on this server")

    try:
        result = subprocess.run(
            ["mkcert", "-CAROOT"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        ca_dir = result.stdout.strip()
        if not ca_dir:
            raise HTTPException(status_code=404, detail="mkcert CA root directory not found")

        ca_file = Path(ca_dir) / "rootCA.pem"
        if not ca_file.exists():
            raise HTTPException(status_code=404, detail="Root CA certificate not found")

        from fastapi.responses import FileResponse

        return FileResponse(
            path=str(ca_file),
            filename="rootCA.pem",
            media_type="application/x-pem-file",
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="mkcert is not installed or CA not found") from exc


# SERVER-LEVEL: pings server-global database connection, CE-only
@router.get("/health/database")
async def check_database_health(
    current_user: User = Depends(get_current_active_user),
    _ce: None = Depends(require_ce_mode),
):
    """Test database connection (requires authentication)"""
    from api.app_state import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database manager not initialized")

    try:
        from giljo_mcp.services.tenant_configuration_service import TenantConfigurationService

        config_service = TenantConfigurationService(
            db_manager=state.db_manager,
            tenant_key=current_user.tenant_key,
        )
        is_healthy = await config_service.execute_health_check()

        if is_healthy:
            return SuccessResponse(message="Database connection successful")
        raise HTTPException(status_code=503, detail="Database health check failed")

    except (RuntimeError, OSError, ValueError) as e:
        logger.error("Database connection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=503, detail="Database connection failed. Check server logs.") from e

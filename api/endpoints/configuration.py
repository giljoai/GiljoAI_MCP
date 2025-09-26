"""
Configuration management API endpoints
"""

import json
from datetime import datetime, timezone
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


@router.get("/", response_model=SystemConfigResponse)
async def get_system_configuration():
    """Get complete system configuration (non-sensitive values only)"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    try:
        # Get safe configuration values (no secrets)
        config = {
            "database": {
                "type": state.config.get("database.type", "sqlite"),
                "pool_size": state.config.get("database.pool_size", 5),
                "max_overflow": state.config.get("database.max_overflow", 10),
                "pool_timeout": state.config.get("database.pool_timeout", 30),
                "echo": state.config.get("database.echo", False),
            },
            "api": {
                "host": state.config.get(
                    "api.host", "0.0.0.0"
                ),  # noqa: S104  # Binding to all interfaces needed for Docker
                "port": state.config.get("api.port", 8000),
                "workers": state.config.get("api.workers", 1),
                "cors_origins": state.config.get("api.cors_origins", ["*"]),
                "max_request_size": state.config.get("api.max_request_size", 10485760),
                "request_timeout": state.config.get("api.request_timeout", 60),
            },
            "orchestration": {
                "max_agents_per_project": state.config.get("orchestration.max_agents_per_project", 10),
                "agent_timeout": state.config.get("orchestration.agent_timeout", 3600),
                "message_retention_days": state.config.get("orchestration.message_retention_days", 30),
                "context_budget_default": state.config.get("orchestration.context_budget_default", 150000),
                "context_warning_threshold": state.config.get("orchestration.context_warning_threshold", 0.8),
            },
            "security": {
                "auth_enabled": state.config.get("security.auth_enabled", False),
                "auth_type": state.config.get("security.auth_type", "api_key"),
                "session_timeout": state.config.get("security.session_timeout", 3600),
                "rate_limiting_enabled": state.config.get("security.rate_limiting_enabled", False),
                "max_requests_per_minute": state.config.get("security.max_requests_per_minute", 60),
            },
            "features": {
                "vision_chunking_enabled": state.config.get("features.vision_chunking_enabled", True),
                "vision_max_tokens": state.config.get("features.vision_max_tokens", 24000),
                "websocket_enabled": state.config.get("features.websocket_enabled", True),
                "telemetry_enabled": state.config.get("features.telemetry_enabled", False),
                "auto_cleanup_enabled": state.config.get("features.auto_cleanup_enabled", True),
            },
        }

        return SystemConfigResponse(**config)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/key/{key_path}", response_model=ConfigurationResponse)
async def get_configuration(key_path: str, default: Optional[Any] = None):
    """Get specific configuration value by key path"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    try:
        # Replace URL path separator with dot notation
        key = key_path.replace("/", ".")
        value = state.config.get(key, default)

        if value is None and default is None:
            raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")  # noqa: TRY301

        # Determine source
        source = "default"
        if hasattr(state.config, "_sources") and key in state.config._sources:  # noqa: SLF001
            source = state.config._sources[key]  # noqa: SLF001

        return ConfigurationResponse(key=key, value=value, source=source, updated_at=datetime.now(timezone.utc))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/key/{key_path}")
async def set_configuration(key_path: str, config: ConfigurationSet):
    """Set configuration value (runtime only, not persisted)"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    try:
        # Replace URL path separator with dot notation
        key = key_path.replace("/", ".")

        # Validate key format
        if not key or ".." in key:
            raise HTTPException(status_code=400, detail="Invalid configuration key")  # noqa: TRY301

        # Set configuration value
        state.config.set(key, config.value)

        return {
            "success": True,
            "key": key,
            "value": config.value,
            "message": "Configuration updated (runtime only)",
        }  # noqa: TRY300

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/")
async def update_configurations(update: ConfigurationUpdate):
    """Update multiple configuration values at once"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    try:
        updated = []
        failed = []

        for key, value in update.configurations.items():
            try:
                state.config.set(key, value)
                updated.append(key)
            except Exception as e:  # noqa: BLE001, PERF203
                failed.append({"key": key, "error": str(e)})

        return {
            "success": len(failed) == 0,
            "updated": updated,
            "failed": failed,
            "message": f"Updated {len(updated)} configurations",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reload")
async def reload_configuration():
    """Reload configuration from files and environment"""
    from api.app import state

    if not state.config:
        raise HTTPException(status_code=503, detail="Configuration manager not available")

    try:
        # Reload configuration
        state.config.reload()

        return {"success": True, "message": "Configuration reloaded successfully"}  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/tenants", response_model=list[str])
async def list_tenant_configurations():
    """List all tenants with custom configurations"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.session() as session:
            from sqlalchemy import distinct, select

            from src.giljo_mcp.models import Configuration

            result = await session.execute(
                select(distinct(Configuration.tenant_key)).where(Configuration.tenant_key.isnot(None))
            )
            tenants = [row[0] for row in result]

            return tenants

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/tenant/{tenant_key}", response_model=dict[str, Any])
async def get_tenant_configuration(tenant_key: str):
    """Get tenant-specific configuration"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.session() as session:
            from sqlalchemy import select

            from src.giljo_mcp.models import Configuration

            result = await session.execute(select(Configuration).where(Configuration.tenant_key == tenant_key))
            configs = result.scalars().all()

            if not configs:
                raise HTTPException(
                    status_code=404, detail=f"No configuration found for tenant '{tenant_key}'"
                )  # noqa: TRY301

            # Build configuration dictionary
            tenant_config = {}
            for config in configs:
                tenant_config[config.key] = json.loads(config.value) if config.value else None

            return tenant_config

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/tenant/{tenant_key}")
async def set_tenant_configuration(
    tenant_key: str,
    configurations: dict[str, Any] = Body(..., description="Tenant-specific configurations"),  # noqa: B008
):
    """Set tenant-specific configuration"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.session() as session:
            from sqlalchemy import select

            from src.giljo_mcp.models import Configuration

            for key, value in configurations.items():
                # Check if configuration exists
                result = await session.execute(
                    select(Configuration).where(Configuration.tenant_key == tenant_key).where(Configuration.key == key)
                )
                config = result.scalar_one_or_none()

                if config:
                    # Update existing
                    config.value = json.dumps(value) if value is not None else None
                    config.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/tenant/{tenant_key}")
async def delete_tenant_configuration(tenant_key: str):
    """Delete all tenant-specific configurations"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.session() as session:
            from sqlalchemy import delete

            from src.giljo_mcp.models import Configuration

            result = await session.execute(delete(Configuration).where(Configuration.tenant_key == tenant_key))

            await session.commit()

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404, detail=f"No configuration found for tenant '{tenant_key}'"
                )  # noqa: TRY301

            return {
                "success": True,
                "tenant_key": tenant_key,
                "configurations_deleted": result.rowcount,
                "message": f"Deleted {result.rowcount} configurations for tenant '{tenant_key}'",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

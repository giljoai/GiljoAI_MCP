"""
Settings API endpoints for GiljoAI MCP.

Provides REST API for system settings management:
- GET/PUT /general - General system settings
- GET/PUT /network - Network configuration
- GET /database - Database settings (read-only)
- GET /product-info - System version and build info
- GET /cookie-domain - Cookie domain configuration

All endpoints enforce multi-tenant isolation and role-based access control.
Handover 0506: Settings endpoints implementation.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin
from src.giljo_mcp.models import User
from src.giljo_mcp.services.settings_service import SettingsService


logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic Models


class SettingsUpdate(BaseModel):
    """Settings update request - settings dict required"""

    settings: dict[str, Any]


class SettingsResponse(BaseModel):
    """Settings response - wraps settings dict"""

    settings: dict[str, Any]


class SettingsUpdateResponse(BaseModel):
    """Settings update response - includes success message"""

    settings: dict[str, Any]
    message: str


class ProductInfoResponse(BaseModel):
    """Product information response"""

    product: str
    version: str
    build: str
    python_version: str
    database: str
    features: list[str]


class CookieDomainResponse(BaseModel):
    """Cookie domain configuration response"""

    cookie_domain: str | None
    secure: bool
    same_site: str


# API Endpoints


@router.get(
    "/general",
    response_model=SettingsResponse,
    summary="Get general settings",
    description="Get general system settings for current tenant",
)
async def get_general_settings(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> SettingsResponse:
    """Get general settings - accessible to all authenticated users"""
    logger.debug(f"User {current_user.username} retrieving general settings")

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.get_settings("general")

    return SettingsResponse(settings=settings)


@router.put(
    "/general",
    response_model=SettingsUpdateResponse,
    summary="Update general settings",
    description="Update general system settings (admin only)",
)
async def update_general_settings(
    request: SettingsUpdate, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db_session)
) -> SettingsUpdateResponse:
    """Update general settings - admin only"""
    logger.info(f"Admin {current_user.username} updating general settings")

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.update_settings("general", request.settings)

    return SettingsUpdateResponse(settings=settings, message="Settings updated successfully")


@router.get(
    "/network",
    response_model=SettingsResponse,
    summary="Get network settings",
    description="Get network configuration for current tenant",
)
async def get_network_settings(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> SettingsResponse:
    """Get network settings - accessible to all authenticated users"""
    logger.debug(f"User {current_user.username} retrieving network settings")

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.get_settings("network")

    return SettingsResponse(settings=settings)


@router.put(
    "/network",
    response_model=SettingsUpdateResponse,
    summary="Update network settings",
    description="Update network configuration (admin only)",
)
async def update_network_settings(
    request: SettingsUpdate, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db_session)
) -> SettingsUpdateResponse:
    """Update network settings - admin only"""
    logger.info(f"Admin {current_user.username} updating network settings")

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.update_settings("network", request.settings)

    return SettingsUpdateResponse(settings=settings, message="Network settings updated successfully")


@router.get(
    "/database",
    response_model=SettingsResponse,
    summary="Get database settings",
    description="Get database configuration for current tenant (read-only)",
)
async def get_database_settings(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> SettingsResponse:
    """Get database settings - read-only for all authenticated users"""
    logger.debug(f"User {current_user.username} retrieving database settings")

    service = SettingsService(db, current_user.tenant_key)
    settings = await service.get_settings("database")

    return SettingsResponse(settings=settings)


@router.get(
    "/product-info",
    response_model=ProductInfoResponse,
    summary="Get product information",
    description="Get GiljoAI MCP version and build information",
)
async def get_product_info(current_user: User = Depends(get_current_active_user)) -> ProductInfoResponse:
    """
    Get product version and build info.

    Returns static product information - no database queries.
    Accessible to all authenticated users.
    """
    logger.debug(f"User {current_user.username} retrieving product info")

    return ProductInfoResponse(
        product="GiljoAI MCP Server",
        version="1.0.0",
        build="production",
        python_version="3.12+",
        database="PostgreSQL 18",
        features=[
            "Multi-tenant orchestration",
            "context prioritization and orchestration",
            "Orchestrator succession",
            "Agent template management",
        ],
    )


@router.get(
    "/cookie-domain",
    response_model=CookieDomainResponse,
    summary="Get cookie domain setting",
    description="Get cookie domain configuration for authentication",
)
async def get_cookie_domain(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> CookieDomainResponse:
    """
    Get cookie domain for authentication.

    Reads from network settings and returns cookie configuration.
    Accessible to all authenticated users.
    """
    logger.debug(f"User {current_user.username} retrieving cookie domain config")

    service = SettingsService(db, current_user.tenant_key)
    network_settings = await service.get_settings("network")

    # Extract cookie settings from network config (defaults to secure same-site)
    cookie_domain = network_settings.get("cookie_domain")
    secure = network_settings.get("cookie_secure", True)
    same_site = network_settings.get("cookie_same_site", "lax")

    return CookieDomainResponse(cookie_domain=cookie_domain, secure=secure, same_site=same_site)

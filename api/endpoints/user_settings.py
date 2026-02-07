"""
User Settings endpoints for authenticated, per-user operations.

This module provides admin-only endpoints for managing cookie domain whitelist
configuration stored in config.yaml.

Project 0031: AI tool configuration is now handled entirely on the
frontend via a mini-wizard. No backend endpoint is provided for
configuration generation.

Project 0036: Cookie domain whitelist management for cross-port authentication.
"""

import logging
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session, require_admin
from src.giljo_mcp.models import User


logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models


class CookieDomainsResponse(BaseModel):
    """Response model for cookie domain whitelist."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"domains": ["localhost", "example.com", "subdomain.example.com"]}}
    )

    domains: List[str] = Field(description="List of whitelisted cookie domains")


class AddCookieDomainRequest(BaseModel):
    """Request model for adding a domain to cookie whitelist."""

    model_config = ConfigDict(json_schema_extra={"example": {"domain": "example.com"}})

    domain: str = Field(
        min_length=3, max_length=255, description="Domain name to whitelist (e.g., 'localhost', 'example.com')"
    )

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """
        Validate domain name format.

        Rules:
        - Must match DNS hostname pattern
        - Cannot be an IP address (IPs are auto-allowed)
        - Min 3 chars, max 255 chars

        Args:
            v: Domain string to validate

        Returns:
            Validated domain string (lowercased)

        Raises:
            ValueError: If domain is invalid
        """
        # Lowercase for consistency
        domain = v.lower().strip()

        # Check min/max length
        if len(domain) < 3:
            raise ValueError("Domain must be at least 3 characters long")
        if len(domain) > 255:
            raise ValueError("Domain must not exceed 255 characters")

        # Reject IP addresses (they're auto-allowed)
        # Simple check: if it looks like an IP (digits and dots only)
        if re.match(r"^[\d.]+$", domain):
            raise ValueError("IP addresses are automatically allowed - only add domain names")

        # Validate domain format
        # RFC 1123 compliant hostname regex
        domain_pattern = (
            r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        )

        if not re.match(domain_pattern, domain):
            raise ValueError(
                "Invalid domain format. Must be a valid DNS hostname "
                "(e.g., 'localhost', 'example.com', 'subdomain.example.com')"
            )

        return domain


class RemoveCookieDomainRequest(BaseModel):
    """Request model for removing a domain from cookie whitelist."""

    model_config = ConfigDict(json_schema_extra={"example": {"domain": "example.com"}})

    domain: str = Field(min_length=3, max_length=255, description="Domain name to remove from whitelist")


# Helper Functions


def _get_config_path() -> Path:
    """Get path to config.yaml in project root."""
    return Path.cwd() / "config.yaml"


def _read_config() -> dict:
    """
    Read config.yaml file.

    Returns:
        Parsed YAML configuration dictionary

    Raises:
        HTTPException: 500 if config file cannot be read
    """
    import yaml

    config_path = _get_config_path()

    try:
        if not config_path.exists():
            logger.error(f"config.yaml not found at {config_path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration file not found. System may not be properly installed.",
            )

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        return config

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse config.yaml: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Configuration file is malformed: {e!s}"
        ) from e
    except Exception as e:
        logger.error(f"Failed to read config.yaml: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read configuration file: {e!s}"
        ) from e


def _write_config(config: dict) -> None:
    """
    Write config.yaml file atomically.

    Args:
        config: Configuration dictionary to write

    Raises:
        HTTPException: 500 if config file cannot be written
    """
    import yaml

    config_path = _get_config_path()

    try:
        # Write to temporary file first (atomic write)
        temp_path = config_path.with_suffix(".yaml.tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

        # Atomic rename
        temp_path.replace(config_path)

        logger.info("config.yaml updated successfully")

    except Exception as e:
        logger.error(f"Failed to write config.yaml: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update configuration file: {e!s}"
        ) from e


def _get_cookie_domains(config: dict) -> List[str]:
    """
    Extract cookie domain whitelist from config.

    Args:
        config: Configuration dictionary

    Returns:
        List of whitelisted domains (empty list if not configured)
    """
    return config.get("security", {}).get("cookie_domain_whitelist", [])


def _set_cookie_domains(config: dict, domains: List[str]) -> None:
    """
    Update cookie domain whitelist in config.

    Ensures security section exists and updates cookie_domain_whitelist.

    Args:
        config: Configuration dictionary (modified in place)
        domains: List of domains to set
    """
    # Ensure security section exists
    if "security" not in config:
        config["security"] = {}

    # Update whitelist
    config["security"]["cookie_domain_whitelist"] = domains


# API Endpoints


@router.get("/settings/cookie-domains", response_model=CookieDomainsResponse)
async def get_cookie_domains(
    current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db_session)
) -> CookieDomainsResponse:
    """
    Get cookie domain whitelist.

    Returns list of domains allowed for cross-port cookie authentication.
    Requires admin role.

    Args:
        current_user: Current authenticated admin user
        db: Database session (required by auth dependency)

    Returns:
        CookieDomainsResponse with list of whitelisted domains

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 500 if config file cannot be read
    """
    logger.info(f"Admin {current_user.username} retrieving cookie domain whitelist")

    # Read config
    config = _read_config()

    # Extract domains
    domains = _get_cookie_domains(config)

    logger.debug(f"Cookie domain whitelist: {domains}")
    return CookieDomainsResponse(domains=domains)


@router.post("/settings/cookie-domains", response_model=CookieDomainsResponse, status_code=status.HTTP_201_CREATED)
async def add_cookie_domain(
    request: AddCookieDomainRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CookieDomainsResponse:
    """
    Add domain to cookie whitelist.

    Adds a domain to the whitelist for cross-port cookie authentication.
    If domain already exists, operation is idempotent (no error).
    Requires admin role.

    Args:
        request: Domain to add
        current_user: Current authenticated admin user
        db: Database session (required by auth dependency)

    Returns:
        Updated CookieDomainsResponse with all whitelisted domains

    Raises:
        HTTPException: 400 if domain validation fails
        HTTPException: 403 if user is not admin
        HTTPException: 500 if config file cannot be updated
    """
    domain = request.domain.lower().strip()
    logger.info(f"Admin {current_user.username} adding cookie domain: {domain}")

    # Read config
    config = _read_config()

    # Get current domains
    domains = _get_cookie_domains(config)

    # Add domain if not already present (idempotent)
    if domain not in domains:
        domains.append(domain)
        logger.info(f"Added domain to whitelist: {domain}")
    else:
        logger.debug(f"Domain already in whitelist: {domain}")

    # Update config
    _set_cookie_domains(config, domains)
    _write_config(config)

    logger.info(f"Cookie domain whitelist updated. Total domains: {len(domains)}")
    return CookieDomainsResponse(domains=domains)


@router.delete("/settings/cookie-domains", response_model=CookieDomainsResponse)
async def remove_cookie_domain(
    request: RemoveCookieDomainRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> CookieDomainsResponse:
    """
    Remove domain from cookie whitelist.

    Removes a domain from the whitelist for cross-port cookie authentication.
    Requires admin role.

    Args:
        request: Domain to remove
        current_user: Current authenticated admin user
        db: Database session (required by auth dependency)

    Returns:
        Updated CookieDomainsResponse with remaining whitelisted domains

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if domain not found in whitelist
        HTTPException: 500 if config file cannot be updated
    """
    domain = request.domain.lower().strip()
    logger.info(f"Admin {current_user.username} removing cookie domain: {domain}")

    # Read config
    config = _read_config()

    # Get current domains
    domains = _get_cookie_domains(config)

    # Remove domain
    if domain not in domains:
        logger.warning(f"Domain not found in whitelist: {domain}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Domain '{domain}' not found in whitelist")

    domains.remove(domain)
    logger.info(f"Removed domain from whitelist: {domain}")

    # Update config
    _set_cookie_domains(config, domains)
    _write_config(config)

    logger.info(f"Cookie domain whitelist updated. Remaining domains: {len(domains)}")
    return CookieDomainsResponse(domains=domains)

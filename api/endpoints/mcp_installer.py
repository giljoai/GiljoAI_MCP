# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MCP Installer API endpoints for downloadable script generation.

Provides REST API for:
- Generating Windows .bat and Unix .sh installer scripts
- Embedding user credentials (server URL, API key, username)
- Creating secure download links with 7-day expiry
- Public download endpoints using tokens

All endpoints support multi-tenant isolation through user authentication.

Phase 2.1 of v3.0 consolidation project.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_user, get_db_session
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# JWT secret for token generation
# Load from environment variable; generate a random secret per-process if unset
_GENERATED_FALLBACK_SECRET = secrets.token_urlsafe(32)
SECRET_KEY = os.getenv("MCP_INSTALLER_SECRET_KEY") or _GENERATED_FALLBACK_SECRET

if SECRET_KEY is _GENERATED_FALLBACK_SECRET:
    logger.warning(
        "MCP_INSTALLER_SECRET_KEY not set. Using ephemeral random secret; "
        "installer download tokens will not survive server restarts. "
        "Set MCP_INSTALLER_SECRET_KEY environment variable for production."
    )

ALGORITHM = "HS256"


# Pydantic Models


class ShareLinkResponse(BaseModel):
    """Response model for share link generation"""

    windows_url: str
    unix_url: str
    expires_at: str
    token: str


# Helper Functions


def get_server_url() -> str:
    """
    Get server URL from configuration, respecting ssl_enabled.

    Returns:
        Server URL (e.g., "https://localhost:7272" or "http://localhost:7272")
    """
    try:
        config = get_config()
        host = config.api.host if hasattr(config, "api") else "localhost"
        port = config.api.port if hasattr(config, "api") else 7272

        # Use localhost if host is 0.0.0.0 (not accessible from external)
        if host == "0.0.0.0":
            host = "localhost"

        protocol = "https" if config.get_nested("features.ssl_enabled", default=False) else "http"
        return f"{protocol}://{host}:{port}"
    except (OSError, ValueError, KeyError) as e:
        logger.warning(f"Failed to get server URL from config: {e}")
        return "http://localhost:7272"


def generate_secure_token(user_id: str, expires_in: int, tenant_key: str = "default") -> str:
    """
    Generate JWT token for script download.

    Args:
        user_id: User identifier
        expires_in: Token expiry in seconds

    Returns:
        JWT token string
    """
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    payload = {
        "user_id": user_id,
        "tenant_key": tenant_key,
        "expires_at": expires_at.isoformat() + "Z",
        "type": "mcp_installer_download",
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def validate_token(token: str) -> Optional[dict]:
    """
    Validate token and return user info.

    Args:
        token: JWT token string

    Returns:
        User info dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check expiration
        expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            logger.warning(f"Token expired: {expires_at}")
            return None

        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token signature expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except (OSError, ValueError, KeyError):
        logger.exception("Token validation error")
        return None


def render_template(
    template_path: Path, server_url: str, api_key: str, username: str, organization: str, timestamp: str
) -> str:
    """
    Render script template with user credentials.

    Args:
        template_path: Path to template file
        server_url: API server URL
        api_key: User's API key
        username: Username
        organization: Organization name or "Personal"
        timestamp: ISO timestamp of generation

    Returns:
        Rendered script content

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template_content = template_path.read_text(encoding="utf-8")

    # Replace placeholders
    script = template_content.format(
        server_url=server_url, api_key=api_key, username=username, organization=organization, timestamp=timestamp
    )

    return script


async def get_user_by_id(session: AsyncSession, user_id: str, tenant_key: str = "default") -> Optional[User]:
    """
    Query user from database by ID.

    NOTE: This is a simple helper function with a straightforward query
    that is only used within this endpoint file. For complex business logic
    or queries used across multiple endpoints, consider adding to a repository.

    Args:
        session: Database session
        user_id: User identifier

    Returns:
        User object or None if not found
    """
    # Defense-in-depth: scope by tenant_key (Handover 0769a)
    stmt = select(User).where(User.id == user_id, User.is_active, User.tenant_key == tenant_key)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return user


# API Endpoints


@router.get("/windows", tags=["MCP Integration"])
async def download_windows_installer(current_user: Optional[User] = Depends(get_current_user)):
    """
    Generate Windows .bat installer with embedded credentials.

    This endpoint generates a Windows batch script that:
    - Auto-detects MCP-compatible tools (Claude Code, Cursor, Windsurf)
    - Configures them with the user's server URL and API key
    - Creates backups before modifying config files
    - Provides detailed installation feedback

    Args:
        current_user: Authenticated user (from JWT or API key)

    Returns:
        Response with .bat file download

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if template not found
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for MCP installer download"
        )

    logger.info(f"Generating Windows installer for user: {current_user.username}")

    # Get template path
    template_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "giljo-mcp-setup.bat.template"

    # Get server URL
    server_url = get_server_url()

    # Get organization name or default to "Personal"
    organization = current_user.organization.name if current_user.organization else "Personal"

    # API keys are stored hashed in the APIKey table and cannot be recovered.
    # The installer template uses a placeholder that the user replaces with
    # their actual key from the dashboard API Keys page.
    api_key = "<YOUR_API_KEY>"

    # Render template
    try:
        script_content = render_template(
            template_path=template_path,
            server_url=server_url,
            api_key=api_key,
            username=current_user.username,
            organization=organization,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        )
    except FileNotFoundError as e:
        logger.exception("Template not found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Installer template not found. Please contact administrator.",
        ) from e

    logger.info(f"Windows installer generated successfully for: {current_user.username}")

    return Response(
        content=script_content,
        media_type="application/bat",
        headers={"Content-Disposition": "attachment; filename=giljo-mcp-setup.bat"},
    )


@router.get("/unix", tags=["MCP Integration"])
async def download_unix_installer(current_user: Optional[User] = Depends(get_current_user)):
    """
    Generate macOS/Linux .sh installer with embedded credentials.

    This endpoint generates a Unix shell script that:
    - Auto-detects MCP-compatible tools (Claude Code, Cursor, Windsurf)
    - Configures them with the user's server URL and API key
    - Creates backups before modifying config files
    - Provides detailed installation feedback

    Args:
        current_user: Authenticated user (from JWT or API key)

    Returns:
        Response with .sh file download

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if template not found
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for MCP installer download"
        )

    logger.info(f"Generating Unix installer for user: {current_user.username}")

    # Get template path
    template_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "giljo-mcp-setup.sh.template"

    # Get server URL
    server_url = get_server_url()

    # Get organization name or default to "Personal"
    organization = current_user.organization.name if current_user.organization else "Personal"

    # API keys are hashed and cannot be recovered from the database.
    api_key = "<YOUR_API_KEY>"

    # Render template
    try:
        script_content = render_template(
            template_path=template_path,
            server_url=server_url,
            api_key=api_key,
            username=current_user.username,
            organization=organization,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        )
    except FileNotFoundError as e:
        logger.exception("Template not found")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Installer template not found. Please contact administrator.",
        ) from e

    logger.info(f"Unix installer generated successfully for: {current_user.username}")

    return Response(
        content=script_content,
        media_type="application/x-sh",
        headers={"Content-Disposition": "attachment; filename=giljo-mcp-setup.sh"},
    )


@router.post("/share-link", response_model=ShareLinkResponse, tags=["MCP Integration"])
async def generate_share_link(current_user: Optional[User] = Depends(get_current_user)):
    """
    Generate secure URLs for script download (email-friendly).

    This endpoint creates a secure token that allows downloading installer
    scripts without authentication. Tokens expire after 7 days.

    Use case: Admin generates links to email to team members who can then
    download the installer scripts without needing to log in.

    Args:
        current_user: Authenticated user (from JWT or API key)

    Returns:
        Share link response with Windows/Unix URLs and expiration

    Raises:
        HTTPException: 401 if not authenticated
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to generate share links"
        )

    logger.info(f"Generating share link for user: {current_user.username}")

    # Generate token with 7-day expiration
    token = generate_secure_token(
        user_id=current_user.id,
        expires_in=7 * 24 * 3600,  # 7 days in seconds
        tenant_key=current_user.tenant_key,
    )

    # Get server URL
    base_url = get_server_url()

    # Generate URLs
    windows_url = f"{base_url}/download/mcp/{token}/windows"
    unix_url = f"{base_url}/download/mcp/{token}/unix"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat() + "Z"

    logger.info(f"Share link generated for {current_user.username}, expires: {expires_at}")

    return ShareLinkResponse(windows_url=windows_url, unix_url=unix_url, expires_at=expires_at, token=token)


@router.get("/download/{token}/{platform}", tags=["MCP Integration"])
async def download_via_token(token: str, platform: str, session: AsyncSession = Depends(get_db_session)):
    """
    Public download endpoint using secure token.

    This endpoint allows downloading installer scripts using a token
    (generated via /share-link). No authentication required - the token
    provides access.

    Args:
        token: Secure JWT token from share link
        platform: "windows" or "unix"
        session: Database session (from dependency)

    Returns:
        Response with script file download

    Raises:
        HTTPException: 401 if token invalid/expired
        HTTPException: 400 if platform invalid
        HTTPException: 500 if template not found
    """
    logger.info(f"Download via token requested: platform={platform}")

    # Validate token
    user_info = validate_token(token)
    if not user_info:
        logger.warning("Invalid/expired token used for download")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Get user from database
    user_id = user_info["user_id"]
    tenant_key = user_info.get("tenant_key", "default")
    user = await get_user_by_id(session, user_id, tenant_key=tenant_key)

    if not user:
        logger.warning(f"User not found for token: {user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Validate platform
    if platform not in ["windows", "unix"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid platform. Must be 'windows' or 'unix'"
        )

    logger.info(f"Token validated for user: {user.username}, platform: {platform}")

    # Generate appropriate script
    if platform == "windows":
        return await download_windows_installer(current_user=user)
    # unix
    return await download_unix_installer(current_user=user)

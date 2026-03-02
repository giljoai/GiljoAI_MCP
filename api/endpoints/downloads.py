"""
Download API endpoints for GiljoAI MCP
Provides ZIP downloads for slash commands and agent templates.

Token-efficient approach: Instead of writing 15K+ tokens of files,
agents download ZIP files via HTTP (~500 tokens).

Handover 0094: Token-Efficient MCP Downloads
"""

import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.tools.slash_command_templates import get_all_templates


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/download", tags=["downloads"])


# Helper Functions


def get_server_url(request=None) -> str:
    """
    Get server URL from configuration, using external_host for public access.

    Args:
        request: Optional request object to detect HTTPS

    Returns:
        Server URL (e.g., "http://10.1.0.164:7272")
    """
    try:
        config = get_config()
        host = config.get_nested("services.external_host", "localhost")
        port = config.server.api_port

        # Detect HTTPS from request headers if available
        scheme = "https" if (request and request.headers.get("x-forwarded-proto") == "https") else "http"

        return f"{scheme}://{host}:{port}"
    except (OSError, ValueError, KeyError) as e:
        logger.warning(f"Failed to get server URL from config: {e}")
        return "http://localhost:7272"


def create_zip_archive(files: dict[str, str]) -> bytes:
    """
    Create ZIP archive from file dictionary.

    Args:
        files: {filename: content} mapping

    Returns:
        ZIP file bytes

    Example:
        >>> files = {"test.md": "# Content"}
        >>> zip_bytes = create_zip_archive(files)
        >>> len(zip_bytes) > 0
        True
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename, content in files.items():
            zipf.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.read()


def generate_yaml_frontmatter(
    name: str,
    role: str,
    tool: str,
    description: Optional[str] = None,
) -> str:
    """
    Generate YAML frontmatter for Claude Code agent template.

    Format:
    ---
    name: orchestrator
    description: Orchestrator agent
    tools: ["mcp__giljo_mcp__*"]
    model: sonnet
    ---

    Args:
        name: Agent name (e.g., "orchestrator")
        role: Agent role (e.g., "orchestrator")
        tool: Preferred AI tool (e.g., "claude")
        description: Optional custom description

    Returns:
        YAML frontmatter string with --- delimiters
    """
    # Use custom description or generate default
    if description is None:
        description = f"{role.capitalize()} agent"

    # Escape description if it contains special YAML characters
    if any(char in description for char in ['"', "'", ":", "\n"]):
        description = description.replace('"', '\\"')
        description = f'"{description}"'

    # Map tool to Claude Code model
    model_map = {
        "claude": "sonnet",
        "codex": "sonnet",
        "gemini": "sonnet",
    }
    model = model_map.get(tool.lower(), "sonnet")

    # Build YAML frontmatter
    yaml_lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        'tools: ["mcp__giljo_mcp__*"]',
        f"model: {model}",
        "---",
    ]

    return "\n".join(yaml_lines) + "\n"


def render_install_script(
    template_content: str,
    server_url: str,
) -> str:
    """
    Render install script template with server URL.

    Args:
        template_content: Script template with {{SERVER_URL}} placeholder
        server_url: Server URL to substitute

    Returns:
        Rendered script content
    """
    return template_content.replace("{{SERVER_URL}}", server_url)


# API Endpoints


@router.get("/slash-commands.zip")
async def download_slash_commands(
    request: Request,
):
    """
    Download slash command templates as complete ZIP file.

    **Public endpoint** - No authentication required.
    Slash commands contain no sensitive data, only markdown instructions.

    This endpoint generates a ZIP file containing:
    - All slash command markdown files with YAML frontmatter
    - install.sh (Unix/macOS/Linux installer)
    - install.ps1 (Windows PowerShell installer)

    Supported commands:
    - gil_get_claude_agents.md (unified agent installer)
    - gil_add.md (unified task/project creation)

    NOTE: gil_activate, gil_launch, gil_handover removed (0388) - users perform these via web UI

    Returns:
        Response with complete ZIP file download

    Example:
        curl http://localhost:7272/api/download/slash-commands.zip -o slash-commands.zip
    """
    logger.info("Generating slash commands ZIP (public download)")

    # Get all slash command templates
    templates = get_all_templates()

    # Add install scripts with server URL rendered
    server_url = get_server_url(request)

    # Read install scripts from templates
    sh_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_slash_commands.sh"
    ps1_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_slash_commands.ps1"

    # Read and render scripts
    if sh_script_path.exists():
        with open(sh_script_path) as f:
            sh_content = render_install_script(f.read(), server_url)
            templates["install.sh"] = sh_content

    if ps1_script_path.exists():
        with open(ps1_script_path) as f:
            ps1_content = render_install_script(f.read(), server_url)
            templates["install.ps1"] = ps1_content

    # Create ZIP archive
    zip_bytes = create_zip_archive(templates)

    logger.info(f"Slash commands ZIP generated: {len(templates)} files, {len(zip_bytes)} bytes")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=slash-commands.zip"},
    )


@router.get("/agent-templates.zip")
async def download_agent_templates(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
    active_only: bool = Query(default=True, description="Only include active templates"),
):
    """
    Download agent templates as complete ZIP file (dynamic content from database).

    **Authentication**: Optional - supports JWT cookie (browser) or API key header (MCP tools).
    - If authenticated: Returns user's tenant-specific customized templates
    - If unauthenticated: Returns system default templates (no sensitive data)

    This endpoint generates a ZIP file containing:
    - All active agent template markdown files with YAML frontmatter
    - install.sh (Unix/macOS/Linux installer for product/personal)
    - install.ps1 (Windows PowerShell installer for product/personal)

    Each template file includes:
    - YAML frontmatter (name, description, tools, model)
    - Template content
    - Behavioral rules (if defined)
    - Success criteria (if defined)

    Args:
        request: FastAPI request
        access_token: Optional JWT cookie (browser session)
        x_api_key: Optional API key header (MCP tools)
        db: Database session
        active_only: Only include active templates (default: True)

    Returns:
        Response with complete ZIP file download

    Example:
        # Authenticated (with browser cookie or API key)
        curl -H "X-API-Key: $KEY" http://localhost:7272/api/download/agent-templates.zip -o templates.zip

        # Unauthenticated (system defaults)
        curl http://localhost:7272/api/download/agent-templates.zip -o templates.zip
    """
    # Try to authenticate (JWT cookie or API key)
    # NOTE: Use get_current_user_optional to avoid raising on unauthenticated access.
    current_user = None
    try:
        from src.giljo_mcp.auth.dependencies import get_current_user_optional

        authorization = request.headers.get("authorization")
        current_user = await get_current_user_optional(
            request,
            access_token,
            x_api_key,
            authorization,
            db,
        )
    except HTTPException:
        # Safety: get_current_user_optional should already swallow HTTPException,
        # but keep this block to avoid leaking auth errors.
        current_user = None

    # Determine template source
    if current_user:
        # Authenticated: Use tenant-specific templates
        logger.info(
            f"Generating agent templates ZIP for user: {current_user.username} "
            f"(tenant: {current_user.tenant_key}, active_only: {active_only})"
        )

        # Query templates with multi-tenant isolation
        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == current_user.tenant_key)
            .order_by(AgentTemplate.name)
        )

        if active_only:
            stmt = stmt.where(AgentTemplate.is_active)

        result = await db.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            logger.warning(f"No templates found for tenant: {current_user.tenant_key} (active_only: {active_only})")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No agent templates found. Please create templates first.",
            )
    else:
        # Unauthenticated: Use system default templates (tenant_key IS NULL)
        logger.info("Generating agent templates ZIP (unauthenticated - system defaults)")

        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key is None).order_by(AgentTemplate.name)

        if active_only:
            stmt = stmt.where(AgentTemplate.is_active)

        result = await db.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            # Fallback: Use hardcoded default template names if no system defaults exist
            logger.warning("No system default templates found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No system default templates available. Please authenticate to access your custom templates.",
            )

    # Build file dictionary using 0102a/0103 renderer and 8-role cap
    from src.giljo_mcp.template_renderer import (
        _slugify_filename,
        render_claude_agent,
        select_templates_for_packaging,
    )

    selected = select_templates_for_packaging(templates, max_count=8)

    files = {}
    for template in selected:
        filename = f"{_slugify_filename(template.name)}.md"
        files[filename] = render_claude_agent(template)

    # Add install scripts with server URL rendered
    server_url = get_server_url(request)

    # Read install scripts from templates
    sh_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_agent_templates.sh"
    ps1_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_agent_templates.ps1"

    # Read and render scripts
    if sh_script_path.exists():
        with open(sh_script_path) as f:
            sh_content = render_install_script(f.read(), server_url)
            files["install.sh"] = sh_content

    if ps1_script_path.exists():
        with open(ps1_script_path) as f:
            ps1_content = render_install_script(f.read(), server_url)
            files["install.ps1"] = ps1_content

    # Create ZIP archive
    zip_bytes = create_zip_archive(files)

    # Handover 0335: Update last_exported_at and emit WebSocket event (authenticated users only)
    if current_user and selected:
        from datetime import datetime, timezone

        export_timestamp = datetime.now(timezone.utc)

        # Update last_exported_at for all exported templates
        for template in selected:
            template.last_exported_at = export_timestamp

        await db.commit()
        logger.info(f"Updated last_exported_at for {len(selected)} templates (tenant: {current_user.tenant_key})")

    user_info = f"user: {current_user.username}" if current_user else "public/unauthenticated"
    logger.info(f"Agent templates ZIP generated ({user_info}): {len(files)} files (max 8), {len(zip_bytes)} bytes")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=agent-templates.zip"},
    )


@router.get("/install-script.{extension}")
async def download_install_script(
    request: Request,
    extension: str,
    script_type: str = Query(..., description="Script type: slash-commands or agent-templates"),
):
    """
    Download cross-platform install script.

    This endpoint generates install scripts for Unix/macOS (.sh) or Windows (.ps1)
    that download and extract ZIP files. Scripts use $GILJO_API_KEY environment
    variable for authentication.

    Supported extensions:
    - .sh (Unix/macOS bash)
    - .ps1 (Windows PowerShell)

    Supported script types:
    - slash-commands
    - agent-templates

    **Public endpoint** - No authentication required.
    Install scripts are public utilities that download from public/optional-auth endpoints.

    Args:
        extension: Script extension (sh or ps1)
        script_type: Type of script (slash-commands or agent-templates)

    Returns:
        Response with script file download

    Raises:
        HTTPException: 400 if invalid extension or type
        HTTPException: 500 if template not found

    Example:
        curl http://localhost:7272/api/download/install-script.sh?script_type=slash-commands -o install.sh
    """
    # Validate extension
    if extension not in ["sh", "ps1"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid extension. Must be 'sh' or 'ps1'",
        )

    # Validate script type
    if script_type not in ["slash-commands", "agent-templates"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid type. Must be 'slash-commands' or 'agent-templates'",
        )

    logger.info(f"Generating install script (public): extension={extension}, type={script_type}")

    # Get server URL
    server_url = get_server_url(request)

    # Get template path
    template_dir = Path(__file__).parent.parent.parent / "installer" / "templates"
    template_filename = f"install_{script_type.replace('-', '_')}.{extension}"
    template_path = template_dir / template_filename

    # Check if template exists
    if not template_path.exists():
        logger.error(f"Install script template not found: {template_path}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Install script template not found. Please contact administrator.",
        )

    # Read and render template
    template_content = template_path.read_text(encoding="utf-8")
    script_content = render_install_script(template_content, server_url)

    # Determine media type
    media_type = "application/x-sh" if extension == "sh" else "application/x-powershell"

    logger.info(f"Install script generated successfully: {len(script_content)} bytes")

    return Response(
        content=script_content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=install.{extension}"},
    )


# ============================================================================
# ONE-TIME TOKEN DOWNLOAD ENDPOINTS
# ============================================================================


@router.post("/generate-token", status_code=status.HTTP_201_CREATED)
async def generate_download_token(
    request: Request,
    content_type: str | None = Query(None, pattern="^(slash_commands|agent_templates)$"),
    db: AsyncSession = Depends(get_db_session),
    body: dict | None = Body(None),
) -> dict:
    """
    Generate one-time download token (requires authentication).

    This endpoint creates a temporary download token that can be used once
    to download the requested content type. Token expires after 15 minutes.

    **Authentication**: Required - JWT cookie or API key header
    **Rate Limiting**: Standard rate limits apply

    Args:
        request: FastAPI request object
        content_type: Type of content to download ('slash_commands' or 'agent_templates')
        db: Database session

    Returns:
        {
            "download_url": "http://server:7272/api/download/temp/{token}/file.zip",
            "expires_at": "2025-11-04T10:45:00Z",
            "content_type": "slash_commands",
            "one_time_use": true
        }

    Raises:
        HTTPException 400: Invalid content_type
        HTTPException 401: Not authenticated
        HTTPException 500: Token generation failed

    Example:
        curl -X POST http://localhost:7272/api/download/generate-token \\
             -H "X-API-Key: $GILJO_API_KEY" \\
             -H "Content-Type: application/json" \\
             -d '{"content_type": "slash_commands"}'
    """
    from src.giljo_mcp.auth.dependencies import get_current_user

    # Get current user (enforces authentication)
    try:
        access_token = request.cookies.get("access_token")
        x_api_key = request.headers.get("x-api-key")
        authorization = request.headers.get("authorization")
        current_user = await get_current_user(request, access_token, x_api_key, authorization, db)
    except HTTPException as e:
        logger.warning("Token generation failed: Authentication required")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to generate download token",
        ) from e

    # Derive content_type from query or JSON body (compat with older tests)
    if not content_type and body:
        content_type = body.get("content_type")

    # Validate content_type
    if content_type not in ["slash_commands", "agent_templates"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content_type. Must be 'slash_commands' or 'agent_templates'",
        )

    logger.info(
        f"Generating download token for user: {current_user.username} "
        f"(tenant: {current_user.tenant_key}, content_type: {content_type})"
    )

    from src.giljo_mcp.downloads.token_manager import TokenManager
    from src.giljo_mcp.file_staging import FileStaging

    tenant_key = current_user.tenant_key
    token_manager = TokenManager(db_session=db)

    # 1) Generate token first (pending)
    filename = "slash_commands.zip" if content_type == "slash_commands" else "agent_templates.zip"
    token = await token_manager.generate_token(
        tenant_key=tenant_key,
        download_type=content_type,
        metadata={"filename": filename, "requested_by": current_user.username},
    )

    # 2) Stage files at temp/{tenant_key}/{token}/
    staging = FileStaging(db_session=db)
    staging_path = await staging.create_staging_directory(tenant_key, token)
    if content_type == "slash_commands":
        zip_path, message = await staging.stage_slash_commands(staging_path)
    else:
        zip_path, message = await staging.stage_agent_templates(staging_path, tenant_key, db_session=db)

    if not zip_path:
        # Mark failed and return error
        await token_manager.mark_failed(token, message)
        logger.error(f"Failed to stage content for token {token}: {message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    # 3) Mark ready
    await token_manager.mark_ready(token)

    # 4) Build download URL and return
    server_url = get_server_url(request)
    download_url = f"{server_url}/api/download/temp/{token}/{filename}"

    token_data = await token_manager.get_token_info(token, tenant_key)
    expires_at = token_data["expires_at"] if token_data else None

    logger.info(f"Token generated and staged successfully: token={token}, type={content_type}, file={zip_path}")
    return {
        "download_url": download_url,
        "expires_at": expires_at,
        "content_type": content_type,
        "one_time_use": True,
    }


@router.get("/temp/{token}/{filename}")
async def download_temp_file(
    token: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Download file using one-time token (public, no auth required).

    This endpoint validates the token and serves the requested file.
    Token validation includes:
    - Token exists and is valid
    - Token not expired (15 minute lifetime)
    - Token not already used (one-time use)
    - Filename matches token metadata

    **Authentication**: NOT required - token IS the authentication
    **Security**: Multi-tenant isolation via token validation

    Args:
        token: One-time download token (UUID)
        filename: Expected filename (must match token metadata)
        request: FastAPI request object
        db: Database session

    Returns:
        File download response with ZIP content

    Raises:
        HTTPException 404: Token invalid, expired, or already used
        HTTPException 410: Token already downloaded (one-time use)
        HTTPException 500: File not found or internal error

    Security Notes:
        - Directory traversal attacks prevented
        - Cross-tenant access denied (returns 404, not 403)
        - No-cache headers prevent stale links
        - File cleanup after download

    Example:
        curl -O http://localhost:7272/api/download/temp/{token}/slash_commands.zip
    """
    logger.info(f"Download request: token={token}, filename={filename}")

    try:
        from src.giljo_mcp.downloads.token_manager import TokenManager
        from src.giljo_mcp.file_staging import FileStaging

        # Validate filename for security
        if not FileStaging.validate_filename(filename):
            logger.warning(f"Invalid filename requested: {filename}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token or file")

        token_manager = TokenManager(db_session=db)

        # Get token info first (no tenant_key needed - token is globally unique)
        token_info = await token_manager.get_token_info_by_token(token)
        if not token_info:
            logger.warning(f"Token validation failed: token={token}, reason=not_found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token invalid or not ready")

        # Check if expired
        if token_info["is_expired"]:
            logger.warning(f"Token validation failed: token={token}, reason=expired")
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download token expired")

        # Check if staging is ready
        if token_info.get("staging_status") != "ready":
            logger.warning(
                f"Token validation failed: token={token}, reason=not_ready, status={token_info.get('staging_status')}"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token invalid or not ready")

        # Check if filename matches metadata
        expected_filename = token_info.get("metadata", {}).get("filename", "")
        if expected_filename != filename:
            logger.warning(f"Token validation failed: token={token}, reason=filename_mismatch")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        # All validations passed
        tenant_key = token_info["tenant_key"]
        safe_token = token_info["token"]  # Use token from DB to avoid path tampering
        # Compute path from token components
        file_path = Path.cwd() / "temp" / tenant_key / safe_token / filename

        if not file_path.exists():
            logger.error(f"File not found for valid token: {file_path}")
            # Maintain compatibility with existing tests expecting 500 here
            # Provide a clearer diagnostic while preserving 'internal' keyword for tests
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error: staged file not found",
            )

        try:
            content = file_path.read_bytes()
        except (OSError, ValueError, KeyError) as e:
            logger.exception("Failed reading file {file_path}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error") from e

        # Increment download metrics
        await token_manager.increment_download_count(token)

        logger.info(f"Download served: {filename} ({len(content)} bytes) token={token}")
        return Response(
            content=content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    except (OSError, ValueError, KeyError) as e:
        logger.exception("Unexpected error during download")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


#
# NOTE: Legacy agent-template installers were removed in Jan 2026.
# Use the `gil_get_claude_agents` slash command (which calls `/api/download/generate-token`)
# for the supported download-and-install flow.

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

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.tools.slash_command_templates import get_all_templates


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/download", tags=["downloads"])


# Helper Functions


def get_server_url(request=None) -> str:
    """
    Get server URL from configuration or request headers.

    Args:
        request: Optional request object to detect HTTPS

    Returns:
        Server URL (e.g., "http://localhost:7272" or "https://example.com:7272")
    """
    try:
        config = get_config()
        host = config.api.host if hasattr(config, "api") else "localhost"
        port = config.api.port if hasattr(config, "api") else 7272

        # Use localhost if host is 0.0.0.0 (not accessible from external)
        if host == "0.0.0.0":
            host = "localhost"

        # Detect HTTPS from request headers if available
        scheme = "https" if (request and request.headers.get("x-forwarded-proto") == "https") else "http"

        return f"{scheme}://{host}:{port}"
    except Exception as e:
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
    - gil_import_productagents.md
    - gil_import_personalagents.md
    - gil_handover.md

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
        with open(sh_script_path, "r") as f:
            sh_content = render_install_script(f.read(), server_url)
            templates["install.sh"] = sh_content

    if ps1_script_path.exists():
        with open(ps1_script_path, "r") as f:
            ps1_content = render_install_script(f.read(), server_url)
            templates["install.ps1"] = ps1_content

    # Create ZIP archive
    zip_bytes = create_zip_archive(templates)

    logger.info(
        f"Slash commands ZIP generated: {len(templates)} files, {len(zip_bytes)} bytes"
    )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=slash-commands.zip"
        },
    )


@router.get("/agent-templates.zip")
async def download_agent_templates(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
    active_only: bool = Query(True, description="Only include active templates"),
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
    current_user = None
    try:
        from src.giljo_mcp.auth.dependencies import get_current_user
        current_user = await get_current_user(request, access_token, x_api_key, db)
    except HTTPException:
        # No auth provided or invalid - will use system defaults
        pass

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
            stmt = stmt.where(AgentTemplate.is_active == True)

        result = await db.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            logger.warning(
                f"No templates found for tenant: {current_user.tenant_key} "
                f"(active_only: {active_only})"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No agent templates found. Please create templates first.",
            )
    else:
        # Unauthenticated: Use system default templates (tenant_key IS NULL)
        logger.info("Generating agent templates ZIP (unauthenticated - system defaults)")

        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == None)
            .order_by(AgentTemplate.name)
        )

        if active_only:
            stmt = stmt.where(AgentTemplate.is_active == True)

        result = await db.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            # Fallback: Use hardcoded default template names if no system defaults exist
            logger.warning("No system default templates found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No system default templates available. Please authenticate to access your custom templates.",
            )

    # Build file dictionary
    files = {}

    for template in templates:
        # Generate filename
        filename = f"{template.name}.md"

        # Generate YAML frontmatter
        frontmatter = generate_yaml_frontmatter(
            name=template.name,
            role=template.role or template.name,
            tool=template.tool,
            description=template.description,
        )

        # Build complete file content
        content_parts = [frontmatter]

        # Add template content
        content_parts.append("\n")
        content_parts.append(template.template_content.strip())
        content_parts.append("\n")

        # Add behavioral rules if present
        if template.behavioral_rules and len(template.behavioral_rules) > 0:
            content_parts.append("\n## Behavioral Rules\n")
            content_parts.extend(f"- {rule}\n" for rule in template.behavioral_rules)

        # Add success criteria if present
        if template.success_criteria and len(template.success_criteria) > 0:
            content_parts.append("\n## Success Criteria\n")
            content_parts.extend(
                f"- {criterion}\n" for criterion in template.success_criteria
            )

        files[filename] = "".join(content_parts)

    # Add install scripts with server URL rendered
    server_url = get_server_url(request)

    # Read install scripts from templates
    sh_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_agent_templates.sh"
    ps1_script_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "install_agent_templates.ps1"

    # Read and render scripts
    if sh_script_path.exists():
        with open(sh_script_path, "r") as f:
            sh_content = render_install_script(f.read(), server_url)
            files["install.sh"] = sh_content

    if ps1_script_path.exists():
        with open(ps1_script_path, "r") as f:
            ps1_content = render_install_script(f.read(), server_url)
            files["install.ps1"] = ps1_content

    # Create ZIP archive
    zip_bytes = create_zip_archive(files)

    user_info = f"user: {current_user.username}" if current_user else "public/unauthenticated"
    logger.info(
        f"Agent templates ZIP generated ({user_info}): "
        f"{len(files)} files, {len(zip_bytes)} bytes"
    )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=agent-templates.zip"
        },
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

    logger.info(
        f"Generating install script (public): extension={extension}, type={script_type}"
    )

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
            detail=f"Install script template not found. Please contact administrator.",
        )

    # Read and render template
    template_content = template_path.read_text(encoding="utf-8")
    script_content = render_install_script(template_content, server_url)

    # Determine media type
    media_type = "application/x-sh" if extension == "sh" else "application/x-powershell"

    logger.info(
        f"Install script generated successfully: {len(script_content)} bytes"
    )

    return Response(
        content=script_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=install.{extension}"
        },
    )

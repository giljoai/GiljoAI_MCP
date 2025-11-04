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

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.tools.slash_command_templates import get_all_templates


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/download", tags=["downloads"])


# Helper Functions


def get_server_url() -> str:
    """
    Get server URL from configuration.

    Returns:
        Server URL (e.g., "http://localhost:7272")
    """
    try:
        config = get_config()
        host = config.api.host if hasattr(config, "api") else "localhost"
        port = config.api.port if hasattr(config, "api") else 7272

        # Use localhost if host is 0.0.0.0 (not accessible from external)
        if host == "0.0.0.0":
            host = "localhost"

        return f"http://{host}:{port}"
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
    current_user: User = Depends(get_current_active_user),
):
    """
    Download slash command templates as ZIP file.

    This endpoint generates a ZIP file containing all slash command markdown files
    with YAML frontmatter. Commands can be installed to ~/.claude/commands/ directory.

    Supported commands:
    - gil_import_productagents.md
    - gil_import_personalagents.md
    - gil_handover.md

    Args:
        current_user: Authenticated user (from JWT or API key)

    Returns:
        Response with ZIP file download

    Raises:
        HTTPException: 401 if not authenticated

    Example:
        curl -H "Authorization: Bearer $TOKEN" \\
             http://localhost:7272/api/download/slash-commands.zip \\
             -o commands.zip
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for slash commands download",
        )

    logger.info(f"Generating slash commands ZIP for user: {current_user.username}")

    # Get all slash command templates
    templates = get_all_templates()

    # Create ZIP archive
    zip_bytes = create_zip_archive(templates)

    logger.info(
        f"Slash commands ZIP generated successfully for: {current_user.username} "
        f"({len(templates)} files, {len(zip_bytes)} bytes)"
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    active_only: bool = Query(True, description="Only include active templates"),
):
    """
    Download agent templates as ZIP file (dynamic content from database).

    This endpoint generates a ZIP file containing agent template markdown files
    with YAML frontmatter. Templates are fetched from the database and filtered
    by the current user's tenant key (multi-tenant isolation).

    Each template file includes:
    - YAML frontmatter (name, description, tools, model)
    - Template content
    - Behavioral rules (if defined)
    - Success criteria (if defined)

    Args:
        current_user: Authenticated user (from JWT or API key)
        db: Database session
        active_only: Only include active templates (default: True)

    Returns:
        Response with ZIP file download

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if no templates found

    Example:
        curl -H "Authorization: Bearer $TOKEN" \\
             http://localhost:7272/api/download/agent-templates.zip?active_only=true \\
             -o templates.zip
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for agent templates download",
        )

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

    # Create ZIP archive
    zip_bytes = create_zip_archive(files)

    logger.info(
        f"Agent templates ZIP generated successfully for: {current_user.username} "
        f"({len(files)} files, {len(zip_bytes)} bytes)"
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
    extension: str,
    script_type: str = Query(..., description="Script type: slash-commands or agent-templates"),
    current_user: User = Depends(get_current_active_user),
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

    Args:
        extension: Script extension (sh or ps1)
        script_type: Type of script (slash-commands or agent-templates)
        current_user: Authenticated user (from JWT or API key)

    Returns:
        Response with script file download

    Raises:
        HTTPException: 400 if invalid extension or type
        HTTPException: 401 if not authenticated
        HTTPException: 500 if template not found

    Example:
        curl -H "Authorization: Bearer $TOKEN" \\
             http://localhost:7272/api/download/install-script.sh?type=slash-commands \\
             -o install.sh
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for install script download",
        )

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
        f"Generating install script for user: {current_user.username} "
        f"(extension: {extension}, type: {script_type})"
    )

    # Get server URL
    server_url = get_server_url()

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
        f"Install script generated successfully for: {current_user.username} "
        f"({len(script_content)} bytes)"
    )

    return Response(
        content=script_content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=install.{extension}"
        },
    )

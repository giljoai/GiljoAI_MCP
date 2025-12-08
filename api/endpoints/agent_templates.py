"""
Agent Template Download API Endpoints

Provides REST endpoints for listing and downloading agent templates as markdown files.
Templates include role-specific missions, MCP tool integration, and behavioral guidelines.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES


logger = logging.getLogger(__name__)
router = APIRouter()
plugin_router = APIRouter()  # Separate router for plugin endpoint (different prefix)


# Pydantic models for responses
class TemplateFileMetadata(BaseModel):
    filename: str = Field(..., description="Template filename (e.g., 'orchestrator.md')")
    url: str = Field(..., description="Download URL for this template")
    role: str = Field(..., description="Agent role this template is for")
    description: Optional[str] = Field(None, description="Template description")
    version: str = Field(..., description="Template version")
    category: str = Field(..., description="Template category")


class TemplateListResponse(BaseModel):
    count: int = Field(..., description="Number of available templates")
    base_url: str = Field(..., description="Base URL for template downloads")
    files: list[TemplateFileMetadata] = Field(..., description="List of available templates")


class PluginTemplate(BaseModel):
    """Agent template response for Claude Code plugin"""
    id: str = Field(..., description="Template UUID")
    name: str = Field(..., description="Human-readable template name")
    role: str = Field(..., description="Agent role identifier")
    category: str = Field(..., description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    full_instructions: str = Field(..., description="Combined system + user instructions")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    version: str = Field(..., description="Template version")
    background_color: Optional[str] = Field(None, description="Hex color code")
    cli_tool: str = Field(default="claude", description="CLI tool: claude, codex, gemini")
    model: Optional[str] = Field(None, description="Model selection")
    is_active: bool = Field(..., description="Whether template is active")  # Required for include_inactive test


class PluginTemplateResponse(BaseModel):
    """Response model for plugin template endpoint"""
    templates: list[PluginTemplate] = Field(..., description="List of agent templates")
    tenant_key: str = Field(..., description="Tenant key used for query")
    count: int = Field(..., description="Number of templates returned")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")


# Rate limiting store (in-memory, simple sliding window)
_rate_limit_store: dict[str, list[datetime]] = defaultdict(list)


def check_rate_limit(tenant_key: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    # Clean old requests
    _rate_limit_store[tenant_key] = [
        t for t in _rate_limit_store[tenant_key] if t > window_start
    ]

    if len(_rate_limit_store[tenant_key]) >= limit:
        return False

    _rate_limit_store[tenant_key].append(now)
    return True


def reset_rate_limit_store() -> None:
    """Reset rate limit store (primarily for testing)"""
    global _rate_limit_store
    _rate_limit_store.clear()


def build_full_instructions(template: AgentTemplate) -> str:
    """Build complete instructions from system + user fields"""
    if template.system_instructions or template.user_instructions:
        system_part = template.system_instructions or ""
        user_part = template.user_instructions or ""
        return f"{system_part}\n\n{user_part}".strip()
    return template.template_content or ""


def generate_default_capabilities(role: str) -> list[str]:
    """Generate default capabilities from role name"""
    tokens = role.lower().replace("-", "_").split("_")
    capabilities = tokens.copy()
    capabilities.extend(["collaboration", "mcp_integration"])
    return capabilities


# MCP Integration section to append to all templates
MCP_INTEGRATION_SECTION = """

## MCP Integration

This agent has access to the following MCP tools for coordinating with the orchestrator and other agents:

### Communication Tools
- `get_agent_messages()` - Check for messages from other agents in your queue (auto-acknowledges)
- `send_agent_message(to, content)` - Send a message to another agent or orchestrator

### Context & Project Information
- `get_project_context(project_id)` - Fetch product vision, tech stack, and project details
- `get_vision_chunk(chunk_id)` - Retrieve specific sections of the product vision document
- `search_vision_content(query)` - Search vision documents for relevant information

### Status & Coordination
- `update_agent_status(status)` - Update your current status (working, blocked, waiting, complete)
- `request_handoff(reason, context)` - Request handoff to another specialized agent
- `report_progress(project_id, progress_data)` - Report task progress to orchestrator

### Task Management
- `create_task(title, description, project_id)` - Create a new technical debt or follow-up task
- `update_task(task_id, updates)` - Update task status or details
- `list_tasks(project_id, filters)` - List tasks for your project

Use these MCP tools throughout your work to maintain coordination, share progress, and ensure the team operates as a cohesive unit.
"""


def format_filename(role: str) -> str:
    """
    Convert role name to filename format

    Args:
        role: Agent role name (e.g., "Orchestrator", "Backend Developer")

    Returns:
        Formatted filename (e.g., "orchestrator.md", "backend-developer.md")
    """
    return role.lower().replace(" ", "-") + ".md"


def build_template_markdown(template: AgentTemplate) -> str:
    """
    Build complete markdown document from template

    Args:
        template: AgentTemplate database object

    Returns:
        Complete markdown content with header and MCP integration section
    """
    # Build template header
    header = f"""# {template.name} Agent Template

**Role:** {template.role or "General"}
**Version:** {template.version}
**Category:** {template.category}
**Description:** {template.description or "No description provided"}

---

"""

    # Combine header + template content + MCP integration
    return header + template.template_content + MCP_INTEGRATION_SECTION


@router.get("/", response_model=TemplateListResponse)
async def list_agent_templates(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    List all available agent templates

    Returns JSON with template metadata and download URLs.
    Only includes active templates (is_active=True).
    Templates are filtered by user's tenant for multi-tenant isolation.

    **Response:**
    - count: Number of templates available
    - base_url: Base URL for constructing download links
    - files: Array of template metadata objects
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Build base URL from config
        # Use external_host if available (for LAN access), otherwise localhost
        config = state.config
        if config:
            host = config.get("services.external_host") or "localhost"
            port = config.server.api_port
        else:
            host = "localhost"
            port = 7272

        base_url = f"http://{host}:{port}/api/v1/agents/templates"

        # Query active templates for user's tenant
        async with state.db_manager.get_session_async() as session:
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == current_user.tenant_key)
                .where(AgentTemplate.is_active == True)
                .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
                .order_by(AgentTemplate.role, AgentTemplate.name)
            )

            result = await session.execute(stmt)
            templates = result.scalars().all()

        # Build template metadata list
        files = []
        for template in templates:
            filename = format_filename(template.role or template.name)
            files.append(
                TemplateFileMetadata(
                    filename=filename,
                    url=f"{base_url}/{filename}",
                    role=template.role or "general",
                    description=template.description,
                    version=template.version,
                    category=template.category,
                )
            )

        logger.info(f"Listed {len(files)} agent templates for tenant {current_user.tenant_key}")

        return TemplateListResponse(count=len(files), base_url=base_url, files=files)

    except Exception as e:
        logger.error(f"Failed to list agent templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@plugin_router.get("/plugin", response_model=PluginTemplateResponse)
async def get_templates_for_plugin(
    tenant_key: str = Query(..., pattern=r"^tk_[A-Za-z0-9]{32}$"),
    include_inactive: bool = Query(False),
):
    """
    Fetch agent templates for Claude Code plugin (no JWT auth required).
    Rate limited to 100 requests/minute per tenant_key.
    Returns empty list for unknown tenants (prevents enumeration).
    """
    from api.app import state

    # Rate limiting
    if not check_rate_limit(tenant_key):
        logger.warning(f"Rate limit exceeded for tenant: {tenant_key}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == tenant_key)
                .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
                .order_by(AgentTemplate.category, AgentTemplate.role)
            )

            if not include_inactive:
                stmt = stmt.where(AgentTemplate.is_active == True)

            result = await session.execute(stmt)
            templates = result.scalars().all()

        # Build response
        plugin_templates = []
        for template in templates:
            full_instructions = build_full_instructions(template)
            capabilities = template.meta_data.get("capabilities", []) if template.meta_data else []
            if not capabilities:
                capabilities = generate_default_capabilities(template.role or "general")

            plugin_templates.append(
                PluginTemplate(
                    id=str(template.id),
                    name=template.name,
                    role=template.role or "general",
                    category=template.category,
                    description=template.description,
                    full_instructions=full_instructions,
                    capabilities=capabilities,
                    version=template.version,
                    background_color=template.background_color,
                    cli_tool=template.cli_tool or "claude",
                    model=template.model,
                    is_active=template.is_active,
                )
            )

        logger.info(f"Plugin: Returned {len(plugin_templates)} templates for {tenant_key}")

        return PluginTemplateResponse(
            templates=plugin_templates,
            tenant_key=tenant_key,
            count=len(plugin_templates),
            cache_ttl=300,
        )

    except Exception as e:
        logger.error(f"Plugin endpoint error for {tenant_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{filename}")
async def download_agent_template(
    filename: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Download an agent template as a markdown file

    **Parameters:**
    - filename: Template filename (e.g., "orchestrator.md")

    **Returns:**
    - Markdown file with template content, header, and MCP integration section
    - Sets Content-Disposition header for download
    - Returns 404 if template not found or inactive

    **Example:**
    ```
    GET /api/v1/agents/templates/orchestrator.md
    ```
    """
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate filename format
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Filename must end with .md")

    # Extract role from filename (remove .md extension, replace hyphens with spaces)
    role = filename[:-3].replace("-", " ")
    if role.strip().lower() in SYSTEM_MANAGED_ROLES:
        raise HTTPException(status_code=404, detail=f"Template '{filename}' not found")

    try:
        # Query template by role and tenant
        async with state.db_manager.get_session_async() as session:
            stmt = (
                select(AgentTemplate)
                .where(AgentTemplate.tenant_key == current_user.tenant_key)
                .where(AgentTemplate.role == role)
                .where(AgentTemplate.is_active == True)
            )

            result = await session.execute(stmt)
            template = result.scalar_one_or_none()

        if not template:
            logger.warning(f"Template not found: {filename} for tenant {current_user.tenant_key}")
            raise HTTPException(status_code=404, detail=f"Template '{filename}' not found or inactive")

        # Build complete markdown content
        markdown_content = build_template_markdown(template)

        logger.info(f"Downloaded template: {filename} (tenant: {current_user.tenant_key})")

        # Return as downloadable markdown file
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download template {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

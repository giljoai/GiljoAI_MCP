"""
Agent Template Download API Endpoints

Provides REST endpoints for listing and downloading agent templates as markdown files.
Templates include role-specific missions, MCP tool integration, and behavioral guidelines.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.services.template_service import TemplateService
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES


logger = logging.getLogger(__name__)
router = APIRouter()


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
- Manage tasks via web interface (Tasks tab) for listing, updating, and deleting

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
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
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

        # Initialize service and get active templates
        template_service = TemplateService()
        templates = await template_service.list_active_user_templates(
            session=session,
            tenant_key=current_user.tenant_key,
        )

        # ORIGINAL QUERY (kept for reference):
        # stmt = (
        #     select(AgentTemplate)
        #     .where(AgentTemplate.tenant_key == current_user.tenant_key)
        #     .where(AgentTemplate.is_active == True)
        #     .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
        #     .order_by(AgentTemplate.role, AgentTemplate.name)
        # )
        # result = await session.execute(stmt)
        # templates = result.scalars().all()

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


@router.get("/{filename}")
async def download_agent_template(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
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
        # Initialize service and get template by role
        template_service = TemplateService()
        template = await template_service.get_template_by_role(
            session=session,
            tenant_key=current_user.tenant_key,
            role=role,
        )

        # ORIGINAL QUERY (kept for reference):
        # stmt = (
        #     select(AgentTemplate)
        #     .where(AgentTemplate.tenant_key == current_user.tenant_key)
        #     .where(AgentTemplate.role == role)
        #     .where(AgentTemplate.is_active == True)
        # )
        # result = await session.execute(stmt)
        # template = result.scalar_one_or_none()

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

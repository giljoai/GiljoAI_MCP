"""
Claude Code Agent Template Export API

Provides REST endpoint for exporting agent templates to Claude Code format
with YAML frontmatter. Supports multi-tenant isolation, automatic backups,
and path validation for security.

Architecture:
- POST /export/claude-code - Export templates to specified directory
- Programmatic export function for orchestrator use
- YAML frontmatter generation for Claude Code compatibility
- Automatic .old.YYYYMMDD_HHMMSS backup creation
- Path validation (only .claude/agents/ directories)
- Multi-tenant isolation (filter by current_user.tenant_key)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import AgentTemplate, User


logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models
class ClaudeExportRequest(BaseModel):
    """Request model for Claude Code template export"""

    export_path: str = Field(
        ...,
        description="Path to .claude/agents/ directory (project or personal)",
        examples=[
            "/path/to/project/.claude/agents",
            "~/.claude/agents",
        ],
    )

    @field_validator("export_path")
    @classmethod
    def validate_export_path(cls, v: str) -> str:
        """Validate that export_path ends with .claude/agents"""
        # Normalize path separators for cross-platform
        normalized = v.replace("\\", "/")

        if not normalized.endswith(".claude/agents"):
            raise ValueError(
                "Export path must end with '.claude/agents' " "(e.g., '/project/.claude/agents' or '~/.claude/agents')"
            )
        return v


class ClaudeExportResult(BaseModel):
    """Result model for Claude Code template export"""

    success: bool = Field(..., description="Whether export succeeded")
    exported_count: int = Field(..., description="Number of templates exported")
    files: list[dict[str, str]] = Field(..., description="List of exported files with name and path")
    message: str = Field(..., description="Human-readable result message")


# Helper Functions
def generate_yaml_frontmatter(
    name: str,
    role: str,
    preferred_tool: str,
    description: Optional[str] = None,
) -> str:
    """
    Generate YAML frontmatter for Claude Code agent template.

    Format:
    ---
    name: orchestrator
    description: Orchestrator - role agent
    tools: ["mcp__giljo_mcp__*"]
    model: sonnet
    ---

    Args:
        name: Agent name (e.g., "orchestrator")
        role: Agent role (e.g., "orchestrator")
        preferred_tool: Preferred AI tool (e.g., "claude")
        description: Optional custom description

    Returns:
        YAML frontmatter string with --- delimiters

    Example:
        >>> frontmatter = generate_yaml_frontmatter("orchestrator", "orchestrator", "claude")
        >>> print(frontmatter)
        ---
        name: orchestrator
        description: Orchestrator - role agent
        tools: ["mcp__giljo_mcp__*"]
        model: sonnet
        ---
    """
    # Use custom description or generate default
    if description is None:
        description = f"{role.capitalize()} - role agent"

    # Escape description if it contains special YAML characters
    if any(char in description for char in ['"', "'", ":", "\n"]):
        # Quote and escape the description
        description = description.replace('"', '\\"')
        description = f'"{description}"'

    # Map preferred_tool to Claude Code model
    model_map = {
        "claude": "sonnet",
        "codex": "sonnet",  # Fallback to sonnet
        "gemini": "sonnet",  # Fallback to sonnet
    }
    model = model_map.get(preferred_tool.lower(), "sonnet")

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


def create_backup(file_path: Path) -> Optional[Path]:
    """
    Create backup of existing file with .old.YYYYMMDD_HHMMSS format.

    Args:
        file_path: Path to file to backup

    Returns:
        Path to backup file if created, None if original didn't exist

    Example:
        >>> backup = create_backup(Path("orchestrator.md"))
        >>> print(backup.name)
        orchestrator.md.old.20251025_143022
    """
    if not file_path.exists():
        return None

    # Generate timestamp in YYYYMMDD_HHMMSS format
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.name}.old.{timestamp}"

    # Copy content to backup
    try:
        backup_path.write_text(file_path.read_text(), encoding="utf-8")
        logger.info(f"Created backup: {backup_path}")
    except Exception as e:
        logger.exception(f"Failed to create backup for {file_path}: {e}")
        raise
    else:
        return backup_path


async def export_template_to_claude_code(
    template_id: str,
    tenant_key: str,
    db: AsyncSession,
    export_path: Path,
) -> str:
    """
    Export SINGLE agent template to Claude Code format.

    Programmatic function for use by orchestrator during agent spawning.
    Exports one specific template to .claude/agents/<role>.md file.

    Args:
        template_id: Template ID to export
        tenant_key: Tenant key for multi-tenant isolation
        db: Database session
        export_path: Path to .claude/agents/ directory (must exist)

    Returns:
        str: Path to exported .md file

    Raises:
        ValueError: If template not found or path invalid
        PermissionError: If tenant doesn't own template

    Example:
        >>> file_path = await export_template_to_claude_code(
        ...     template_id="tpl-123",
        ...     tenant_key="tenant-abc",
        ...     db=session,
        ...     export_path=Path.cwd() / ".claude" / "agents"
        ... )
        >>> print(file_path)
        F:/project/.claude/agents/implementer.md
    """
    # Validate export path exists
    if not export_path.exists():
        raise ValueError(f"Export directory does not exist: {export_path}")

    if not export_path.is_dir():
        raise ValueError(f"Export path is not a directory: {export_path}")

    # Query template with tenant isolation
    stmt = select(AgentTemplate).where(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == tenant_key,
    )

    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise ValueError(f"Template {template_id} not found for tenant {tenant_key}")

    # Generate filename
    filename = f"{template.name}.md"
    file_path = export_path / filename

    # Create backup if file exists
    if file_path.exists():
        create_backup(file_path)

    # Generate YAML frontmatter
    frontmatter = generate_yaml_frontmatter(
        name=template.name,
        role=template.role or template.name,
        preferred_tool=template.tool,  # Use 'tool' field
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
        content_parts.extend(f"- {criterion}\n" for criterion in template.success_criteria)

    # Write file
    full_content = "".join(content_parts)
    file_path.write_text(full_content, encoding="utf-8")

    logger.info(
        f"[export_template_to_claude_code] Exported template {template.name} " f"to {file_path} for tenant {tenant_key}"
    )

    return str(file_path)


async def export_templates_to_claude_code(
    db: AsyncSession,
    current_user: User,
    export_path: str,
) -> dict[str, Any]:
    """
    Export agent templates to Claude Code format.

    Programmatic function for use by orchestrator and API endpoints.
    Exports all active templates for user's tenant to specified directory.

    Process:
    1. Validate export path (must end with .claude/agents/)
    2. Expand home directory if needed (~)
    3. Query active templates for user's tenant
    4. Create backup of existing files
    5. Generate YAML frontmatter + template content
    6. Write files to disk
    7. Return export results

    Args:
        db: Database session
        current_user: Authenticated user (for tenant isolation)
        export_path: Path to .claude/agents/ directory

    Returns:
        Dictionary with export results:
        {
            "success": True,
            "exported_count": 3,
            "files": [
                {"name": "orchestrator", "path": "/path/orchestrator.md"},
                ...
            ],
            "message": "Successfully exported 3 templates"
        }

    Raises:
        ValueError: If path validation fails or directory doesn't exist
        HTTPException: If database query fails

    Example:
        >>> result = await export_templates_to_claude_code(
        ...     db=session,
        ...     current_user=user,
        ...     export_path="/project/.claude/agents"
        ... )
        >>> print(result["exported_count"])
        3
    """
    # Validate export path
    normalized_path = export_path.replace("\\", "/")
    if not normalized_path.endswith(".claude/agents"):
        raise ValueError(
            "Export path must end with '.claude/agents' " "(e.g., '/project/.claude/agents' or '~/.claude/agents')"
        )

    # Expand home directory
    export_dir = Path(export_path).expanduser()

    # Verify directory exists
    if not export_dir.exists():
        raise ValueError(
            f"Export directory does not exist: {export_dir}\n"
            "Please create the directory first or verify the path is correct."
        )

    if not export_dir.is_dir():
        raise ValueError(f"Export path is not a directory: {export_dir}")

    # Query active templates for user's tenant (multi-tenant isolation)
    stmt = (
        select(AgentTemplate)
        .where(
            AgentTemplate.tenant_key == current_user.tenant_key,
            AgentTemplate.is_active,
        )
        .order_by(AgentTemplate.name)
    )

    result = await db.execute(stmt)
    templates = result.scalars().all()

    if not templates:
        logger.warning(f"No active templates found for tenant: {current_user.tenant_key}")
        return {
            "success": True,
            "exported_count": 0,
            "files": [],
            "message": "No active templates found for export",
        }

    # Export each template
    exported_files = []

    for template in templates:
        try:
            # Generate filename
            filename = f"{template.name}.md"
            file_path = export_dir / filename

            # Create backup if file exists
            if file_path.exists():
                create_backup(file_path)

            # Generate YAML frontmatter
            frontmatter = generate_yaml_frontmatter(
                name=template.name,
                role=template.role or template.name,
                preferred_tool=template.tool,
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
                content_parts.extend(f"- {criterion}\n" for criterion in template.success_criteria)

            # Write file
            full_content = "".join(content_parts)
            file_path.write_text(full_content, encoding="utf-8")

            logger.info(f"Exported template: {template.name} to {file_path}")

            exported_files.append(
                {
                    "name": template.name,
                    "path": str(file_path),
                }
            )

        except Exception as e:
            logger.exception(f"Failed to export template {template.name}: {e}")
            # Continue with other templates rather than failing completely
            continue

    # Return results
    return {
        "success": True,
        "exported_count": len(exported_files),
        "files": exported_files,
        "message": f"Successfully exported {len(exported_files)} template(s) to {export_dir}",
    }


# API Endpoint
@router.post(
    "/export/claude-code",
    response_model=ClaudeExportResult,
    summary="Export agent templates to Claude Code format",
    description=(
        "Export all active agent templates for current user's tenant to "
        "Claude Code format with YAML frontmatter. Creates automatic backups "
        "of existing files. Path must end with .claude/agents/."
    ),
    responses={
        200: {
            "description": "Templates exported successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "exported_count": 3,
                        "files": [
                            {
                                "name": "orchestrator",
                                "path": "/project/.claude/agents/orchestrator.md",
                            }
                        ],
                        "message": "Successfully exported 3 template(s)",
                    }
                }
            },
        },
        400: {"description": "Invalid export path"},
        401: {"description": "Not authenticated"},
        500: {"description": "Export failed"},
    },
)
async def export_claude_code_endpoint(
    request: ClaudeExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ClaudeExportResult:
    """
    Export agent templates to Claude Code format.

    Exports all active agent templates for the current user's tenant to the
    specified directory in Claude Code format with YAML frontmatter.

    Features:
    - Multi-tenant isolation (only exports user's tenant templates)
    - Automatic backup creation (.old.YYYYMMDD_HHMMSS)
    - YAML frontmatter generation
    - Behavioral rules and success criteria appending
    - Path validation for security

    Args:
        request: Export request with target directory path
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        Export result with success status and file list

    Raises:
        HTTPException: 400 if path invalid, 401 if not authenticated, 500 if export fails

    Example Request:
        POST /export/claude-code
        {
            "export_path": "/my-project/.claude/agents"
        }

    Example Response:
        {
            "success": true,
            "exported_count": 3,
            "files": [
                {"name": "orchestrator", "path": "/my-project/.claude/agents/orchestrator.md"},
                {"name": "analyzer", "path": "/my-project/.claude/agents/analyzer.md"},
                {"name": "implementor", "path": "/my-project/.claude/agents/implementor.md"}
            ],
            "message": "Successfully exported 3 template(s) to /my-project/.claude/agents"
        }
    """
    try:
        result = await export_templates_to_claude_code(
            db=db,
            current_user=current_user,
            export_path=request.export_path,
        )

        return ClaudeExportResult(**result)

    except ValueError as e:
        # Path validation errors
        logger.warning(f"Export path validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from None

    except Exception as e:
        # Unexpected errors
        logger.exception(f"Export failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {e!s}",
        ) from e

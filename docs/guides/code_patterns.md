# Implementation Code Patterns
## Direct Code Examples with Line Numbers

---

## 1. File Download Response Pattern
**Source**: `api/endpoints/mcp_installer.py:274-280`

```python
return Response(
    content=script_content,
    media_type="application/bat",
    headers={
        "Content-Disposition": "attachment; filename=giljo-mcp-setup.bat"
    }
)
```

**For Different File Types**:
- ZIP: `media_type="application/zip", filename="backup.zip"`
- JSON: `media_type="application/json", filename="data.json"`
- CSV: `media_type="text/csv", filename="data.csv"`
- PDF: `media_type="application/pdf", filename="doc.pdf"`

---

## 2. ZIP File Generation Pattern
**Source**: `api/endpoints/claude_export.py:174-237`

```python
def create_zip_backup(agents_dir: Path) -> Optional[Path]:
    """Create timestamped zip backup of .claude/agents/ directory"""
    
    # 1. Check if directory exists
    if not agents_dir.exists() or not agents_dir.is_dir():
        logger.info(f"No agents directory to backup: {agents_dir}")
        return None
    
    # 2. Find .md files to backup
    md_files = list(agents_dir.glob("*.md"))
    if not md_files:
        logger.info(f"No .md files to backup in {agents_dir}")
        return None
    
    # 3. Create backups directory
    backups_dir = agents_dir.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Generate timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"agents_backup_{timestamp}.zip"
    backup_path = backups_dir / backup_filename
    
    # 5. Create zip archive
    try:
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for md_file in md_files:
                zipf.write(md_file, arcname=md_file.name)
                logger.debug(f"Added to zip: {md_file.name}")
        
        logger.info(
            f"Created backup: {backup_path} "
            f"({len(md_files)} files, {backup_path.stat().st_size} bytes)"
        )
        return backup_path
        
    except Exception as e:
        logger.exception(f"Failed to create backup: {e}")
        return None
```

---

## 3. Endpoint Template with Authentication
**Source**: `api/endpoints/mcp_installer.py:210-280`

```python
@router.get("/windows", tags=["MCP Integration"])
async def download_windows_installer(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Generate Windows .bat installer with embedded credentials.
    
    This endpoint generates a Windows batch script that:
    - Auto-detects MCP-compatible tools
    - Configures them with the user's server URL and API key
    - Creates backups before modifying config files
    
    Args:
        current_user: Authenticated user (from JWT or API key)
    
    Returns:
        Response with .bat file download
    
    Raises:
        HTTPException: 401 if not authenticated, 500 if template not found
    """
    
    # 1. Validate authentication
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for MCP installer download"
        )
    
    logger.info(f"Generating Windows installer for user: {current_user.username}")
    
    # 2. Get template and configuration
    template_path = Path(__file__).parent.parent.parent / "installer" / "templates" / "giljo-mcp-setup.bat.template"
    server_url = get_server_url()
    organization = current_user.organization.name if current_user.organization else "Personal"
    api_key = getattr(current_user, 'api_key', f'gk_{current_user.username}_default')
    
    # 3. Render template with context
    try:
        script_content = render_template(
            template_path=template_path,
            server_url=server_url,
            api_key=api_key,
            username=current_user.username,
            organization=organization,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except FileNotFoundError as e:
        logger.error(f"Template not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Installer template not found. Please contact administrator."
        )
    
    logger.info(f"Windows installer generated successfully for: {current_user.username}")
    
    # 4. Return file response
    return Response(
        content=script_content,
        media_type="application/bat",
        headers={
            "Content-Disposition": "attachment; filename=giljo-mcp-setup.bat"
        }
    )
```

---

## 4. Multi-Tenant Database Query Pattern
**Source**: `api/endpoints/templates.py:212-298`

```python
@router.get("/", response_model=list[TemplateResponse])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all templates with optional filtering.
    Returns templates for the current user's tenant.
    
    Security:
    - Multi-tenant isolation: Only returns templates for user's tenant_key
    - Authentication required via JWT
    """
    
    start_time = time.time()
    
    try:
        from src.giljo_mcp.models import AgentTemplate
        
        context = get_tenant_and_product_from_user(current_user)
        
        # Build query with tenant isolation
        filters = [
            AgentTemplate.tenant_key == context["tenant_key"],
        ]
        
        # Optional is_active filter
        if is_active is not None:
            filters.append(AgentTemplate.is_active == is_active)
        
        # Build statement
        stmt = select(AgentTemplate).where(and_(*filters))
        
        # Apply additional filters
        if category:
            stmt = stmt.where(AgentTemplate.category == category)
        if role:
            stmt = stmt.where(AgentTemplate.role == role)
        
        stmt = stmt.order_by(AgentTemplate.name)
        
        # Execute query
        result = await session.execute(stmt)
        templates = result.scalars().all()
        
        response_time = (time.time() - start_time) * 1000
        
        # Convert to response models
        responses = []
        for template in templates:
            responses.append(
                TemplateResponse(
                    id=template.id,
                    tenant_key=template.tenant_key,
                    product_id=template.product_id,
                    name=template.name,
                    category=template.category,
                    # ... more fields
                )
            )
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 5. Pydantic Request/Response Models
**Source**: `api/endpoints/claude_export.py:37-71`

```python
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
                "Export path must end with '.claude/agents' "
                "(e.g., '/project/.claude/agents' or '~/.claude/agents')"
            )
        return v


class ClaudeExportResult(BaseModel):
    """Result model for Claude Code template export"""
    
    success: bool = Field(..., description="Whether export succeeded")
    exported_count: int = Field(..., description="Number of templates exported")
    files: list[dict[str, str]] = Field(..., description="List of exported files with name and path")
    message: str = Field(..., description="Human-readable result message")
    backup: Optional[dict[str, Any]] = Field(None, description="Backup information (Handover 0075)")
```

---

## 6. Export Function Pattern (Programmatic)
**Source**: `api/endpoints/claude_export.py:338-441`

```python
async def export_templates_to_claude_code(
    db: AsyncSession,
    current_user: User,
    export_path: str,
) -> dict[str, Any]:
    """
    Export agent templates to Claude Code format.
    
    Process:
    1. Validate export path (must end with .claude/agents/)
    2. Expand home directory if needed (~)
    3. Query active templates for user's tenant
    4. Create backup of existing files
    5. Generate YAML frontmatter + template content
    6. Write files to disk
    7. Return export results
    """
    
    # 1. Validate export path
    normalized_path = export_path.replace("\\", "/")
    if not normalized_path.endswith(".claude/agents"):
        raise ValueError(
            "Export path must end with '.claude/agents' "
            "(e.g., '/project/.claude/agents' or '~/.claude/agents')"
        )
    
    # 2. Expand home directory
    export_dir = Path(export_path).expanduser()
    
    # 3. Verify directory exists
    if not export_dir.exists():
        raise ValueError(
            f"Export directory does not exist: {export_dir}\n"
            "Please create the directory first or verify the path is correct."
        )
    
    if not export_dir.is_dir():
        raise ValueError(f"Export path is not a directory: {export_dir}")
    
    # 4. Create backup before export (Handover 0075)
    backup_path = create_zip_backup(export_dir)
    backup_info = None
    if backup_path:
        backup_info = {
            "backup_created": True,
            "backup_path": str(backup_path),
            "backup_size_bytes": backup_path.stat().st_size,
        }
        logger.info(f"Created pre-export backup: {backup_path}")
    else:
        backup_info = {"backup_created": False, "reason": "No existing files to backup"}
    
    # 5. Query active templates for user's tenant (multi-tenant isolation)
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
    
    # 6. Export each template
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
    
    # 7. Return results (including backup info)
    base_message = f"Successfully exported {len(exported_files)} template(s) to {export_dir}"
    if len(templates) > 8:
        base_message += " (Warning: exporting more than 8 agents may reduce available context in Claude Code)"
    
    return {
        "success": True,
        "exported_count": len(exported_files),
        "files": exported_files,
        "backup": backup_info,
        "message": base_message,
    }
```

---

## 7. Error Handling and Logging Pattern
**Source**: `api/endpoints/claude_export.py:605-625`

```python
@router.post(
    "/export/claude-code",
    response_model=ClaudeExportResult,
    summary="Export agent templates to Claude Code format",
)
async def export_claude_code_endpoint(
    request: ClaudeExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ClaudeExportResult:
    """Export agent templates to Claude Code format"""
    
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
```

---

## 8. YAML Frontmatter Generation
**Source**: `api/endpoints/claude_export.py:74-138`

```python
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
```

---

## 9. Router Registration
**Source**: `api/app.py:531`

```python
# Import endpoint module
from .endpoints import claude_export

# Register router with prefix and tags
app.include_router(
    claude_export.router,
    prefix="/api",
    tags=["claude-export"]
)
```

---

## 10. Authentication in Endpoint
**Source**: `api/endpoints/mcp_installer.py:284-306`

```python
@router.get("/unix", tags=["MCP Integration"])
async def download_unix_installer(
    current_user: Optional[User] = Depends(get_current_user)
):
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
        HTTPException: 401 if not authenticated, 500 if template not found
    """
    
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for MCP installer download"
        )
    
    logger.info(f"Generating Unix installer for user: {current_user.username}")
    
    # ... rest of implementation
```

---

**End of Code Patterns Document**

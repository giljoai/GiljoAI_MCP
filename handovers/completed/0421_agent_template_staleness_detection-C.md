---
**Handover**: 0421 - Agent Template Staleness Detection in get_available_agents() MCP Tool
**Type**: Backend
**Effort**: 4-5 hours
**Priority**: P1
**Status**: Planning
---

# Handover 0421: Agent Template Staleness Detection in get_available_agents() MCP Tool

## Problem Statement

Orchestrators can stage projects with agent templates that are stale (modified in MCP server database but not re-exported to local `.claude/agents/` files). This causes silent failures during implementation phase when the orchestrator invokes `Task(subagent_type="X", ...)` and the executor cannot find the template or uses an outdated version.

### Current Behavior

```
1. User edits "tdd-implementor" template in dashboard → saved to database
2. Orchestrator stages project via get_available_agents() → sees "tdd-implementor" is available
3. Orchestrator spawns "tdd-implementor" job → creates database record
4. User runs /gil_launch → orchestrator attempts Task(subagent_type="tdd-implementor", ...)
5. SILENT FAILURE: Local .claude/agents/tdd-implementor.md is stale or missing
```

### Root Cause

**Dashboard staleness detection exists** but **orchestrators cannot see it:**
- ✅ `AgentTemplate.may_be_stale` property exists (checks `updated_at > last_exported_at`)
- ✅ Dashboard export button updates `last_exported_at` timestamp
- ❌ `/gil_get_claude_agents` slash command does NOT update `last_exported_at` (BUG)
- ❌ `get_available_agents()` MCP tool does NOT return staleness information

This creates a **verification gap** where orchestrators make decisions based on incomplete information.

---

## Scope

### Included

1. **Fix `/gil_get_claude_agents` export tracking** (File: `src/giljo_mcp/file_staging.py`)
   - Update `last_exported_at` when templates are exported via token-based download
   - Ensures staleness detection works for both UI and slash command exports

2. **Add staleness detection to `get_available_agents()` response** (File: `src/giljo_mcp/tools/agent_discovery.py`)
   - Return `may_be_stale`, `last_exported_at`, `updated_at` fields per agent
   - Include self-describing warning structure with actionable guidance
   - Zero token bloat to prompts (all data in tool RESPONSE only)

3. **Comprehensive testing**
   - Unit tests for staleness property and export timestamp updates
   - Integration tests for orchestrator discovery workflow
   - End-to-end test for export → staleness cycle

### Excluded

- Automatic export triggering (orchestrator asks user)
- Dashboard UI changes (staleness detection already visible there)
- Agent template migration logic (handled separately)
- Validation of local file existence (orchestrator can use Glob tool if needed)

---

## Tasks

**Phase 1: Fix Export Timestamp Update**
- [ ] Update `FileStaging.stage_agent_templates()` to update `last_exported_at` for all exported templates
- [ ] Add database session commit after timestamp update
- [ ] Add logging for export timestamp updates
- [ ] Write unit test: `test_stage_agent_templates_updates_export_timestamp()`

**Phase 2: Enhance get_available_agents() Response**
- [ ] Add staleness fields to `_format_agent_info()` helper function
- [ ] Add staleness warning structure to `get_available_agents()` response
- [ ] Preserve zero-token-bloat design (no prompt changes)
- [ ] Write unit test: `test_get_available_agents_includes_staleness_info()`

**Phase 3: Integration Testing**
- [ ] E2E test: Export templates → modify template → verify staleness=true
- [ ] E2E test: Re-export templates → verify staleness=false
- [ ] E2E test: Orchestrator calls get_available_agents() → receives staleness warning
- [ ] Verify token count (response data, not prompt tokens)

**Phase 4: Documentation**
- [ ] Update MCP_TOOLS_MANUAL.md with new response fields
- [ ] Add orchestrator workflow guidance for staleness handling
- [ ] Update CLAUDE.md with export timestamp fix
- [ ] Create completion summary in this handover

---

## Success Criteria

✅ **Export Timestamp Tracking**
- `/gil_get_claude_agents` updates `last_exported_at` for all exported templates
- Dashboard export button continues to update `last_exported_at` (no regression)
- Timestamp updates persist to database after export completes

✅ **Staleness Detection in MCP Tool**
- `get_available_agents()` returns `may_be_stale`, `last_exported_at`, `updated_at` per agent
- Response includes `staleness_warning` structure when stale agents detected
- Warning provides actionable guidance: "Run /gil_get_claude_agents to sync, or continue?"

✅ **Zero Token Bloat**
- No changes to orchestrator thin prompt (~450-550 tokens preserved)
- No changes to orchestrator protocol/instructions
- Staleness data appears only in tool RESPONSE (~50 tokens added to response)

✅ **Testing Coverage**
- Unit tests for `FileStaging.stage_agent_templates()` timestamp update
- Unit tests for `get_available_agents()` staleness fields
- Integration test for export → modify → staleness cycle
- E2E test for orchestrator discovery workflow

✅ **Documentation**
- MCP_TOOLS_MANUAL.md documents new response format
- Orchestrator workflow docs include staleness handling guidance
- Code comments explain export timestamp update logic

---

## Implementation

### Part 1: Fix Export Timestamp Update

**File**: `src/giljo_mcp/file_staging.py`

**Current Code** (lines 157-226):
```python
async def stage_agent_templates(
    self,
    staging_path: Path,
    tenant_key: str,
    db_session: Optional[AsyncSession] = None,
) -> Tuple[Optional[Path], str]:
    """Stage agent templates as a ZIP file."""
    session = db_session or self.db_session
    if not session:
        return (None, "Database session not configured for template staging")

    try:
        # Query active templates for tenant
        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True)
        )

        result = await session.execute(stmt)
        all_active = result.scalars().all()

        if not all_active:
            msg = f"No active templates found for tenant: {tenant_key}"
            logger.warning(msg)
            return (None, msg)

        # Apply packaging selection (cap to 8 templates)
        from .template_renderer import _slugify_filename, render_claude_agent, select_templates_for_packaging

        selected = select_templates_for_packaging(all_active, max_count=8)

        # Create ZIP file with Claude-compatible YAML/Markdown
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for template in selected:
                filename = f"{_slugify_filename(template.name)}.md"
                content = render_claude_agent(template)
                zf.writestr(filename, content)

        logger.info(
            f"Staged agent templates ZIP: {zip_path} ({len(selected)} files from {len(all_active)} active templates)"
        )
        return (zip_path, f"Successfully staged {len(selected)} agent templates")
    except OSError as e:
        msg = f"Disk error staging agent templates: {e}"
        logger.error(msg)
        return (None, msg)
    except Exception as e:
        msg = f"Unexpected error staging agent templates: {e}"
        logger.error(msg)
        return (None, msg)
```

**Required Changes**:
```python
async def stage_agent_templates(
    self,
    staging_path: Path,
    tenant_key: str,
    db_session: Optional[AsyncSession] = None,
) -> Tuple[Optional[Path], str]:
    """
    Stage agent templates as a ZIP file.

    Queries the database for active agent templates belonging to the
    tenant and creates a ZIP file with .md files.

    **Handover 0421**: Updates last_exported_at timestamp for all exported templates
    to enable staleness detection in get_available_agents().

    Args:
        staging_path: Pre-created staging directory (temp/{tenant_key}/{token}/)
        tenant_key: Tenant identifier
        db_session: Optional DB session override

    Returns:
        Tuple (zip_path|None, message)

    Raises:
        None - returns (None, message) on error
    """
    session = db_session or self.db_session
    if not session:
        return (None, "Database session not configured for template staging")

    try:
        from datetime import datetime, timezone  # Add import

        staging_path.mkdir(parents=True, exist_ok=True)
        zip_path = staging_path / "agent_templates.zip"

        # Query active templates for tenant
        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True)
        )

        result = await session.execute(stmt)
        all_active = result.scalars().all()

        if not all_active:
            msg = f"No active templates found for tenant: {tenant_key}"
            logger.warning(msg)
            return (None, msg)

        # Apply packaging selection (cap to 8 templates)
        from .template_renderer import _slugify_filename, render_claude_agent, select_templates_for_packaging

        selected = select_templates_for_packaging(all_active, max_count=8)

        # Create ZIP file with Claude-compatible YAML/Markdown
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for template in selected:
                filename = f"{_slugify_filename(template.name)}.md"
                content = render_claude_agent(template)
                zf.writestr(filename, content)

        # ═══════════════════════════════════════════════════════════════════════
        # Handover 0421: Update export timestamp for staleness detection
        # ═══════════════════════════════════════════════════════════════════════
        export_timestamp = datetime.now(timezone.utc)
        template_ids = [t.id for t in selected]

        for template in selected:
            template.last_exported_at = export_timestamp

        await session.commit()

        logger.info(
            f"Updated last_exported_at for {len(selected)} templates at {export_timestamp.isoformat()}"
        )
        # ═══════════════════════════════════════════════════════════════════════

        logger.info(
            f"Staged agent templates ZIP: {zip_path} ({len(selected)} files from {len(all_active)} active templates)"
        )
        return (zip_path, f"Successfully staged {len(selected)} agent templates")
    except OSError as e:
        msg = f"Disk error staging agent templates: {e}"
        logger.error(msg)
        return (None, msg)
    except Exception as e:
        msg = f"Unexpected error staging agent templates: {e}"
        logger.error(msg)
        # Rollback on error
        if session:
            await session.rollback()
        return (None, msg)
```

**Key Changes**:
1. Import `datetime` and `timezone`
2. After ZIP creation, update `last_exported_at` for all selected templates
3. Commit changes to database
4. Add rollback on error
5. Log export timestamp update

---

### Part 2: Add Staleness Detection to get_available_agents()

**File**: `src/giljo_mcp/tools/agent_discovery.py`

**Current Code** (lines 35-78):
```python
def _format_agent_info(template: AgentTemplate, depth: str = "full") -> dict[str, Any]:
    """Format agent template into discovery response format."""
    version = template.version or DEFAULT_VERSION

    # Base information (always included)
    agent_info = {
        "name": template.name,
        "role": template.role or DEFAULT_ROLE,
        "version_tag": version,
    }

    # Add additional fields based on depth level
    if depth == "full":
        # Truncate description if too long
        description = ""
        if template.description:
            description = (
                template.description[:MAX_DESCRIPTION_LENGTH]
                if len(template.description) > MAX_DESCRIPTION_LENGTH
                else template.description
            )

        agent_info.update({
            "description": description,
            "expected_filename": f"{template.name}_{version}.md",
            "created_at": template.created_at.isoformat() if template.created_at else None,
        })

    return agent_info
```

**Required Changes**:
```python
def _format_agent_info(template: AgentTemplate, depth: str = "full") -> dict[str, Any]:
    """
    Format agent template into discovery response format.

    Args:
        template: AgentTemplate database model instance
        depth: Detail level - "type_only" (name/role/version) or "full" (includes description)

    Returns:
        dict with formatted agent information

    Note:
        Handles missing fields gracefully with sensible defaults.

    Handover 0283: Added depth parameter for context depth configuration.
    Handover 0421: Added staleness detection fields (may_be_stale, last_exported_at, updated_at).
    """
    # Handle missing version gracefully
    version = template.version or DEFAULT_VERSION

    # Base information (always included)
    agent_info = {
        "name": template.name,
        "role": template.role or DEFAULT_ROLE,
        "version_tag": version,
    }

    # Add staleness detection fields (Handover 0421)
    agent_info.update({
        "may_be_stale": template.may_be_stale,
        "last_exported_at": template.last_exported_at.isoformat() if template.last_exported_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    })

    # Add additional fields based on depth level
    if depth == "full":
        # Truncate description if too long
        description = ""
        if template.description:
            description = (
                template.description[:MAX_DESCRIPTION_LENGTH]
                if len(template.description) > MAX_DESCRIPTION_LENGTH
                else template.description
            )

        agent_info.update({
            "description": description,
            "expected_filename": f"{template.name}_{version}.md",
            "created_at": template.created_at.isoformat() if template.created_at else None,
        })

    return agent_info
```

**Current Code** (lines 81-184):
```python
async def get_available_agents(session: AsyncSession, tenant_key: str, depth: str = "full") -> dict[str, Any]:
    """Get available agent templates with version metadata."""
    try:
        # Input validation
        if not tenant_key or not isinstance(tenant_key, str):
            logger.warning("Invalid tenant_key provided to get_available_agents")
            return {
                "success": True,
                "data": {
                    "agents": [],
                    "count": 0,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Invalid tenant key - no agents available",
                },
            }

        logger.info("Fetching available agents", extra={"tenant_key": tenant_key, "depth": depth})

        # Fetch active templates for this tenant
        stmt = (
            select(AgentTemplate)
            .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
            .order_by(AgentTemplate.created_at)
        )

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata (apply depth filtering)
        agents = [_format_agent_info(template, depth=depth) for template in templates]

        logger.info(f"Found {len(agents)} available agents (depth={depth})",
                   extra={"tenant_key": tenant_key, "count": len(agents), "depth": depth})

        return {
            "success": True,
            "data": {
                "agents": agents,
                "count": len(agents),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "note": f"Templates fetched dynamically ({depth} depth)",
            },
        }

    except Exception:
        logger.exception("Failed to fetch available agents", extra={"tenant_key": tenant_key})
        return {
            "success": False,
            "error": "Database error occurred while fetching agents",
            "fallback": "Unable to discover agents. Check server connectivity.",
        }
```

**Required Changes**:
```python
async def get_available_agents(session: AsyncSession, tenant_key: str, depth: str = "full") -> dict[str, Any]:
    """
    Get available agent templates with version metadata.

    Used by orchestrators to discover available agents without
    requiring embedded templates in prompts.

    Args:
        session: Database session
        tenant_key: Tenant isolation key
        depth: Detail level - "type_only" (name/role/version only, ~50 tokens) or
               "full" (includes description, ~1.2k tokens). Default: "full"

    Returns:
        dict with agents list and version metadata

    Example Response (depth="full", with staleness):
        {
            "success": True,
            "data": {
                "agents": [
                    {
                        "name": "implementer",
                        "role": "Code Implementation Specialist",
                        "description": "...",
                        "version_tag": "1.2.0",
                        "may_be_stale": true,
                        "last_exported_at": "2025-12-20T10:00:00Z",
                        "updated_at": "2025-12-28T15:00:00Z",
                        "expected_filename": "implementer_1.2.0.md",
                        "created_at": "2025-11-24T12:00:00"
                    }
                ],
                "count": 5,
                "fetched_at": "2025-11-24T12:30:00",
                "note": "Templates fetched dynamically (full depth)",
                "staleness_warning": {
                    "has_stale_agents": true,
                    "stale_count": 1,
                    "stale_agents": ["implementer"],
                    "action_required": "Some agent templates may be outdated. Run /gil_get_claude_agents to sync, or continue anyway?",
                    "options": ["Run /gil_get_claude_agents", "Continue anyway", "Abort staging"]
                }
            }
        }

    Handover 0283: Added depth parameter for context depth configuration.
    Handover 0421: Added staleness detection with warning structure.
    """
    try:
        # Input validation
        if not tenant_key or not isinstance(tenant_key, str):
            logger.warning("Invalid tenant_key provided to get_available_agents")
            return {
                "success": True,
                "data": {
                    "agents": [],
                    "count": 0,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Invalid tenant key - no agents available",
                },
            }

        logger.info("Fetching available agents", extra={"tenant_key": tenant_key, "depth": depth})

        # Fetch active templates for this tenant
        stmt = (
            select(AgentTemplate)
            .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
            .order_by(AgentTemplate.created_at)
        )

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata (apply depth filtering)
        agents = [_format_agent_info(template, depth=depth) for template in templates]

        # ═══════════════════════════════════════════════════════════════════════
        # Handover 0421: Add staleness warning structure
        # ═══════════════════════════════════════════════════════════════════════
        stale_agents = [agent["name"] for agent in agents if agent.get("may_be_stale", False)]
        staleness_warning = None

        if stale_agents:
            staleness_warning = {
                "has_stale_agents": True,
                "stale_count": len(stale_agents),
                "stale_agents": stale_agents,
                "action_required": (
                    "Some agent templates have been modified since last export. "
                    "Local .claude/agents/ files may be outdated. "
                    "Run /gil_get_claude_agents to sync, or continue anyway?"
                ),
                "options": [
                    "Run /gil_get_claude_agents",
                    "Continue anyway (risk using stale templates)",
                    "Abort staging"
                ],
            }
            logger.warning(
                f"Staleness detected: {len(stale_agents)} stale agent(s) found",
                extra={"tenant_key": tenant_key, "stale_agents": stale_agents}
            )
        # ═══════════════════════════════════════════════════════════════════════

        logger.info(f"Found {len(agents)} available agents (depth={depth})",
                   extra={"tenant_key": tenant_key, "count": len(agents), "depth": depth})

        response_data = {
            "agents": agents,
            "count": len(agents),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "note": f"Templates fetched dynamically ({depth} depth)",
        }

        # Add staleness warning only if stale agents detected (Handover 0421)
        if staleness_warning:
            response_data["staleness_warning"] = staleness_warning

        return {
            "success": True,
            "data": response_data,
        }

    except Exception:
        logger.exception("Failed to fetch available agents", extra={"tenant_key": tenant_key})
        return {
            "success": False,
            "error": "Database error occurred while fetching agents",
            "fallback": "Unable to discover agents. Check server connectivity.",
        }
```

**Key Changes**:
1. Add staleness fields to `_format_agent_info()` (always included, regardless of depth)
2. Build staleness warning structure in `get_available_agents()`
3. Include warning only if stale agents detected (conditional field)
4. Log staleness detection for debugging
5. Update docstring with example response

---

## Testing

### Unit Tests

**File**: `tests/tools/test_agent_discovery.py`

```python
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.tools.agent_discovery import get_available_agents, _format_agent_info


@pytest.mark.asyncio
async def test_format_agent_info_includes_staleness_fields(db_session: AsyncSession):
    """Test that _format_agent_info() includes staleness detection fields."""
    # Create template with staleness
    now = datetime.now(timezone.utc)
    template = AgentTemplate(
        id="test-template-1",
        tenant_key="tenant-abc",
        name="test-agent",
        role="Tester",
        version="1.0.0",
        template_content="Test template",
        is_active=True,
        updated_at=now,
        last_exported_at=now - timedelta(days=1),  # Exported 1 day ago
    )

    # Format with full depth
    result = _format_agent_info(template, depth="full")

    # Verify staleness fields present
    assert "may_be_stale" in result
    assert result["may_be_stale"] is True  # updated_at > last_exported_at
    assert "last_exported_at" in result
    assert "updated_at" in result
    assert result["last_exported_at"] == (now - timedelta(days=1)).isoformat()
    assert result["updated_at"] == now.isoformat()


@pytest.mark.asyncio
async def test_get_available_agents_includes_staleness_warning(db_session: AsyncSession):
    """Test that get_available_agents() includes staleness warning when stale agents detected."""
    # Create stale template
    now = datetime.now(timezone.utc)
    stale_template = AgentTemplate(
        id="stale-template",
        tenant_key="tenant-abc",
        name="stale-agent",
        role="Stale Role",
        version="1.0.0",
        template_content="Stale template",
        is_active=True,
        updated_at=now,
        last_exported_at=now - timedelta(days=1),
    )

    # Create fresh template
    fresh_template = AgentTemplate(
        id="fresh-template",
        tenant_key="tenant-abc",
        name="fresh-agent",
        role="Fresh Role",
        version="1.0.0",
        template_content="Fresh template",
        is_active=True,
        updated_at=now - timedelta(days=2),
        last_exported_at=now,
    )

    db_session.add_all([stale_template, fresh_template])
    await db_session.commit()

    # Call get_available_agents
    result = await get_available_agents(db_session, "tenant-abc", depth="full")

    # Verify response structure
    assert result["success"] is True
    assert "data" in result
    assert "agents" in result["data"]
    assert "staleness_warning" in result["data"]

    # Verify staleness warning
    warning = result["data"]["staleness_warning"]
    assert warning["has_stale_agents"] is True
    assert warning["stale_count"] == 1
    assert "stale-agent" in warning["stale_agents"]
    assert "fresh-agent" not in warning["stale_agents"]
    assert "action_required" in warning
    assert "options" in warning
    assert len(warning["options"]) == 3


@pytest.mark.asyncio
async def test_get_available_agents_no_staleness_warning_when_all_fresh(db_session: AsyncSession):
    """Test that staleness_warning is omitted when all agents are fresh."""
    # Create fresh template
    now = datetime.now(timezone.utc)
    fresh_template = AgentTemplate(
        id="fresh-template",
        tenant_key="tenant-abc",
        name="fresh-agent",
        role="Fresh Role",
        version="1.0.0",
        template_content="Fresh template",
        is_active=True,
        updated_at=now - timedelta(days=1),
        last_exported_at=now,
    )

    db_session.add(fresh_template)
    await db_session.commit()

    # Call get_available_agents
    result = await get_available_agents(db_session, "tenant-abc", depth="full")

    # Verify staleness_warning is NOT present
    assert result["success"] is True
    assert "staleness_warning" not in result["data"]
```

**File**: `tests/test_file_staging.py`

```python
import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.file_staging import FileStaging


@pytest.mark.asyncio
async def test_stage_agent_templates_updates_export_timestamp(db_session: AsyncSession, tmp_path: Path):
    """Test that stage_agent_templates() updates last_exported_at for exported templates."""
    # Create templates
    template1 = AgentTemplate(
        id="template-1",
        tenant_key="tenant-abc",
        name="agent-one",
        role="Role One",
        version="1.0.0",
        template_content="Template 1",
        is_active=True,
        last_exported_at=None,  # Never exported
    )
    template2 = AgentTemplate(
        id="template-2",
        tenant_key="tenant-abc",
        name="agent-two",
        role="Role Two",
        version="1.0.0",
        template_content="Template 2",
        is_active=True,
        last_exported_at=None,
    )

    db_session.add_all([template1, template2])
    await db_session.commit()

    # Create staging instance
    staging = FileStaging(base_path=tmp_path, db_session=db_session)
    staging_dir = tmp_path / "tenant-abc" / "test-token"

    # Stage templates
    before_export = datetime.now(timezone.utc)
    zip_path, msg = await staging.stage_agent_templates(staging_dir, "tenant-abc", db_session)
    after_export = datetime.now(timezone.utc)

    # Verify export succeeded
    assert zip_path is not None
    assert zip_path.exists()
    assert "Successfully staged" in msg

    # Refresh templates from database
    await db_session.refresh(template1)
    await db_session.refresh(template2)

    # Verify last_exported_at was updated
    assert template1.last_exported_at is not None
    assert template2.last_exported_at is not None
    assert before_export <= template1.last_exported_at <= after_export
    assert before_export <= template2.last_exported_at <= after_export

    # Verify both templates have same export timestamp
    assert template1.last_exported_at == template2.last_exported_at


@pytest.mark.asyncio
async def test_stage_agent_templates_preserves_staleness_after_export(db_session: AsyncSession, tmp_path: Path):
    """Test that may_be_stale becomes False after export."""
    # Create stale template
    now = datetime.now(timezone.utc)
    template = AgentTemplate(
        id="stale-template",
        tenant_key="tenant-abc",
        name="stale-agent",
        role="Stale Role",
        version="1.0.0",
        template_content="Stale template",
        is_active=True,
        updated_at=now,
        last_exported_at=now - timedelta(days=1),  # Exported 1 day ago
    )

    db_session.add(template)
    await db_session.commit()

    # Verify template is stale before export
    assert template.may_be_stale is True

    # Export template
    staging = FileStaging(base_path=tmp_path, db_session=db_session)
    staging_dir = tmp_path / "tenant-abc" / "test-token"
    zip_path, msg = await staging.stage_agent_templates(staging_dir, "tenant-abc", db_session)

    # Refresh from database
    await db_session.refresh(template)

    # Verify template is no longer stale
    assert template.may_be_stale is False
    assert template.last_exported_at >= template.updated_at
```

### Integration Test

**File**: `tests/integration/test_orchestrator_staleness_workflow.py`

```python
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.tools.agent_discovery import get_available_agents
from src.giljo_mcp.file_staging import FileStaging


@pytest.mark.asyncio
async def test_orchestrator_staleness_detection_workflow(db_session: AsyncSession, tmp_path):
    """
    End-to-end test for orchestrator staleness detection workflow.

    Workflow:
    1. User edits template in dashboard (simulated via DB update)
    2. Orchestrator calls get_available_agents() → receives staleness warning
    3. User runs /gil_get_claude_agents (simulated via FileStaging export)
    4. Orchestrator calls get_available_agents() → no staleness warning
    """
    # Step 1: Create template and export it
    now = datetime.now(timezone.utc)
    template = AgentTemplate(
        id="test-template",
        tenant_key="tenant-abc",
        name="test-agent",
        role="Test Role",
        version="1.0.0",
        template_content="Original template",
        is_active=True,
        updated_at=now - timedelta(days=2),
        last_exported_at=now - timedelta(days=1),  # Exported 1 day ago
    )
    db_session.add(template)
    await db_session.commit()

    # Step 2: User edits template (simulate dashboard update)
    template.template_content = "Updated template"
    template.updated_at = now  # Updated now, but last_exported_at is stale
    await db_session.commit()

    # Step 3: Orchestrator calls get_available_agents()
    result = await get_available_agents(db_session, "tenant-abc", depth="full")

    # Verify staleness warning present
    assert result["success"] is True
    assert "staleness_warning" in result["data"]
    assert result["data"]["staleness_warning"]["has_stale_agents"] is True
    assert "test-agent" in result["data"]["staleness_warning"]["stale_agents"]

    # Step 4: User runs /gil_get_claude_agents (simulate export)
    staging = FileStaging(base_path=tmp_path, db_session=db_session)
    staging_dir = tmp_path / "tenant-abc" / "test-token"
    zip_path, msg = await staging.stage_agent_templates(staging_dir, "tenant-abc", db_session)

    # Verify export succeeded
    assert zip_path is not None
    assert "Successfully staged" in msg

    # Refresh template
    await db_session.refresh(template)

    # Verify template is no longer stale
    assert template.may_be_stale is False

    # Step 5: Orchestrator calls get_available_agents() again
    result2 = await get_available_agents(db_session, "tenant-abc", depth="full")

    # Verify staleness warning is gone
    assert result2["success"] is True
    assert "staleness_warning" not in result2["data"]
```

---

## Token Budget Analysis

### Zero Token Bloat to Prompts

**Orchestrator Thin Prompt** (no changes):
- Current: ~450-550 tokens
- After Handover 0421: ~450-550 tokens (unchanged)
- ✅ Zero impact

**Orchestrator Protocol/Instructions** (no changes):
- Current: ~1,253 tokens (6-phase generic agent template)
- After Handover 0421: ~1,253 tokens (unchanged)
- ✅ Zero impact

### Token Cost in Tool Response

**get_available_agents() Response** (additional fields):

**Per-Agent Staleness Fields** (~15 tokens per agent):
```json
{
  "may_be_stale": true,
  "last_exported_at": "2025-12-28T15:00:00Z",
  "updated_at": "2025-12-30T10:00:00Z"
}
```

**Staleness Warning Structure** (~35 tokens, only when stale agents detected):
```json
{
  "staleness_warning": {
    "has_stale_agents": true,
    "stale_count": 1,
    "stale_agents": ["implementer"],
    "action_required": "Some agent templates have been modified since last export...",
    "options": ["Run /gil_get_claude_agents", "Continue anyway", "Abort staging"]
  }
}
```

**Total Token Impact**:
- 5 agents × 15 tokens = ~75 tokens (staleness fields)
- 35 tokens (warning structure, conditional)
- **Total: ~110 tokens added to tool response** (not prompt)

**Justification**:
- This is response data, not prompt overhead
- Orchestrator only pays token cost when calling `get_available_agents()`
- Warning provides actionable guidance, preventing silent failures
- Alternative (silent failure) costs 1000s of tokens in debugging/retry cycles

---

## Rollback

If issues arise, rollback in reverse order:

### Step 1: Revert get_available_agents() Changes
```bash
git revert <commit-hash-for-part-2>
```

**What reverts**:
- Staleness fields removed from `_format_agent_info()`
- Staleness warning structure removed from `get_available_agents()`
- Response format returns to pre-0421 structure

**Side effects**: None (backward compatible - orchestrators will ignore missing fields)

### Step 2: Revert Export Timestamp Update
```bash
git revert <commit-hash-for-part-1>
```

**What reverts**:
- `FileStaging.stage_agent_templates()` no longer updates `last_exported_at`
- Export timestamp tracking returns to dashboard-only behavior

**Side effects**: Staleness detection will only work for UI exports, not slash command exports (known limitation prior to 0421)

### Step 3: Verify Database State
No database migrations required - all changes are runtime-only (existing columns used).

**Manual verification**:
```sql
-- Check that last_exported_at timestamps are reasonable
SELECT name, last_exported_at, updated_at
FROM agent_templates
WHERE tenant_key = 'your-tenant-key';
```

---

## Related Handovers

- **0382**: Orchestrator Prompt Improvements (Issue 1 was export status validation - partial solution)
- **0246c**: Dynamic Agent Discovery & Token Reduction (introduced `get_available_agents()` tool)
- **0335**: Export tracking implementation (added `last_exported_at` column)
- **0100**: One-Liner Installation (`/gil_get_claude_agents` slash command)

---

## Future Enhancements (Out of Scope)

1. **Automatic Export Triggering**
   - Orchestrator could auto-trigger `/gil_get_claude_agents` when staleness detected
   - Requires user consent workflow (security consideration)

2. **Local File Validation**
   - Orchestrator verifies `.claude/agents/*.md` files exist locally
   - Cross-checks file content hash vs database version

3. **Staleness Dashboard Alert**
   - Add visual indicator in dashboard when templates are stale
   - One-click "Export All Stale Templates" button

4. **Template Version Pinning**
   - Allow orchestrators to pin specific template versions
   - Prevents unexpected behavior from template updates mid-project

---

## Documentation Updates

**Files to Update**:
1. `docs/manuals/MCP_TOOLS_MANUAL.md`
   - Document new `get_available_agents()` response fields
   - Add staleness warning structure example
   - Include workflow guidance for handling staleness

2. `docs/ORCHESTRATOR.md`
   - Add section on staleness detection
   - Document recommended workflow: check staleness → ask user → export if needed

3. `CLAUDE.md`
   - Update "Agent Template Management" section
   - Document export timestamp fix
   - Add staleness detection to known features

4. `handovers/0421_agent_template_staleness_detection.md`
   - Complete this handover with completion summary
   - Document actual vs estimated effort
   - Lessons learned section

---

## Completion Summary

**To be filled after implementation**

**Completed**: [Date]
**Effort**: [Actual hours] (estimated: 4-5 hours)
**Commits**: [Commit hashes]
**Coverage**: [Test coverage %]

### What Was Delivered
- [ ] Export timestamp tracking in `/gil_get_claude_agents`
- [ ] Staleness detection in `get_available_agents()` response
- [ ] Comprehensive test suite (unit, integration, E2E)
- [ ] Documentation updates (MCP_TOOLS_MANUAL, ORCHESTRATOR, CLAUDE.md)

### Lessons Learned
[To be filled]

### Follow-Up Items
[To be filled]

---

**Status**: Planning → Ready for Implementation
